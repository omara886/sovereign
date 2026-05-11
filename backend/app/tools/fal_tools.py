import io
import logging

import httpx
from PIL import Image
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    """Generate image via fal.ai REST API."""
    if not settings.FAL_KEY:
        logger.warning("FAL_KEY not set — using placeholder")
        return _placeholder(width, height)

    logger.info("fal.ai request: model=%s size=%dx%d prompt=%.80s", model, width, height, prompt)

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"https://fal.run/{model}",
                headers={"Authorization": f"Key {settings.FAL_KEY}"},
                json={"prompt": prompt, "image_size": {"width": width, "height": height}, "num_images": 1},
            )
            if not r.is_success:
                logger.error("fal.ai error %d: %s", r.status_code, r.text[:200])
                return _placeholder(width, height)

            data = r.json()
            images = data.get("images") or data.get("image") or []
            if not images:
                logger.error("fal.ai no images in response: %s", str(data)[:200])
                return _placeholder(width, height)

            image_url = images[0]["url"] if isinstance(images[0], dict) else images[0]
            logger.info("fal.ai image URL: %s", image_url[:80])

            img_r = await client.get(image_url)
            img_r.raise_for_status()
            logger.info("fal.ai image downloaded: %d bytes", len(img_r.content))
            return img_r.content

    except Exception as exc:
        logger.error("fal.ai exception: %s", exc)
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    """Warm dark branded placeholder — used when fal.ai unavailable."""
    img = Image.new("RGB", (width, height), color=(30, 35, 42))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
