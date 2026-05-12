import io
import logging

import httpx
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)


async def generate_image_fal(
    prompt: str,
    model: str,
    width: int,
    height: int,
    negative_prompt: str = "",
    num_inference_steps: int = 4,
    guidance_scale: float = 3.5,
) -> bytes:
    settings = get_settings()
    if not settings.FAL_KEY:
        logger.warning("FAL_KEY not set — using placeholder")
        return _placeholder(width, height)

    try:
        import fal_client
        import os
        os.environ["FAL_KEY"] = settings.FAL_KEY

        # Base arguments — schnell uses fewer steps, dev uses more + supports negative prompt
        arguments: dict = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "enable_safety_checker": False,
            "output_format": "jpeg",
        }

        # Add inference params based on model capability
        if "schnell" in model:
            arguments["num_inference_steps"] = min(num_inference_steps, 4)
        else:
            arguments["num_inference_steps"] = max(num_inference_steps, 20)
            arguments["guidance_scale"] = guidance_scale
            if negative_prompt:
                arguments["negative_prompt"] = negative_prompt

        logger.info("fal.ai %s | %dx%d | prompt=%.80s", model, width, height, prompt[:80])

        def _log_update(update):
            logger.debug("fal.ai update: %s", update)

        result = await fal_client.subscribe_async(
            model,
            arguments=arguments,
            with_logs=False,
            on_queue_update=_log_update,
        )

        images = result.get("images") or []
        if not images:
            logger.error("fal.ai returned no images: %s", result)
            return _placeholder(width, height)

        image = images[0]
        image_url = image["url"] if isinstance(image, dict) else image
        async with httpx.AsyncClient(timeout=60) as client:
            img_r = await client.get(image_url, timeout=60)
            img_r.raise_for_status()
            return img_r.content
    except Exception as e:
        logger.error("fal.ai exception: %s", type(e).__name__, exc_info=True)
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 26, 77))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
