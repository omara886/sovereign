import asyncio
import io
from PIL import Image

from app.config import get_settings

settings = get_settings()


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    """Generate image via fal.ai API. Falls back to placeholder if FAL_KEY not set."""
    fal_key = settings.FAL_KEY
    if not fal_key:
        return _placeholder_image(width, height)

    try:
        import fal_client

        handler = await asyncio.to_thread(
            fal_client.run,
            model,
            arguments={
                "prompt": prompt,
                "image_size": {"width": width, "height": height},
                "num_inference_steps": 4 if "schnell" in model else 28,
                "num_images": 1,
            },
        )
        image_url = handler["images"][0]["url"]

        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    except Exception:
        return _placeholder_image(width, height)


def _placeholder_image(width: int, height: int) -> bytes:
    """Dark slate placeholder with gold border — matches design system."""
    img = Image.new("RGB", (width, height), color=(30, 41, 59))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
