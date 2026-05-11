import io
import logging

import httpx
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    settings = get_settings()
    if not settings.FAL_KEY:
        logger.warning("FAL_KEY not set — using placeholder")
        return _placeholder(width, height)

    try:
        import fal_client

        arguments = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "num_inference_steps": 4,
            "guidance_scale": 3.5,
            "enable_safety_checker": False,
            "output_format": "png",
        }

        logger.info("fal.ai subscribe %s | %dx%d | prompt=%.60s", model, width, height, prompt)

        def _log_update(update):
            logger.info("fal.ai queue update: %s", update)

        result = await fal_client.subscribe_async(
            model,
            arguments=arguments,
            with_logs=True,
            on_queue_update=_log_update,
        )
        logger.info("fal.ai result keys: %s", list(result.keys()))
        images = result.get("images") or []
        if not images:
            logger.error("fal.ai returned no images: %s", result)
            return _placeholder(width, height)

        image = images[0]
        image_url = image["url"] if isinstance(image, dict) else image
        logger.info("fal.ai image url: %s", image_url)
        async with httpx.AsyncClient(timeout=60) as client:
            img_r = await client.get(image_url, timeout=60)
            img_r.raise_for_status()
            logger.info("fal.ai downloaded %d bytes", len(img_r.content))
            return img_r.content
    except Exception as e:
        logger.error("fal.ai exception: %s", type(e).__name__, exc_info=True)
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(30, 35, 42))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
