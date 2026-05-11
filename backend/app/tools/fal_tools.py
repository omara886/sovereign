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

    # fal.ai correct endpoint format
    url = f"https://fal.run/{model}"
    headers = {
        "Authorization": f"Key {settings.FAL_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
        "enable_safety_checker": False,
    }

    logger.info("fal.ai POST %s | %dx%d | prompt=%.60s", url, width, height, prompt)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=headers, json=body)
            logger.info("fal.ai response: %d | %s", r.status_code, r.text[:200])
            r.raise_for_status()
            data = r.json()
            images = data.get("images", [])
            if not images:
                logger.error("fal.ai returned no images: %s", data)
                return _placeholder(width, height)
            image_url = images[0]["url"]
            logger.info("fal.ai image url: %s", image_url)
            img_r = await client.get(image_url, timeout=60)
            img_r.raise_for_status()
            logger.info("fal.ai downloaded %d bytes", len(img_r.content))
            return img_r.content
    except httpx.HTTPStatusError as e:
        logger.error("fal.ai HTTP error %d: %s", e.response.status_code, e.response.text[:300])
        return _placeholder(width, height)
    except Exception as e:
        logger.error("fal.ai exception: %s", type(e).__name__, exc_info=True)
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(30, 35, 42))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
