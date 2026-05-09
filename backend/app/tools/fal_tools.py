import io
import httpx
from PIL import Image
from app.config import get_settings

settings = get_settings()


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    """Generate image via fal.ai REST API. Falls back to placeholder if FAL_KEY not set."""
    if not settings.FAL_KEY:
        return _placeholder(width, height)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"https://fal.run/{model}",
                headers={"Authorization": f"Key {settings.FAL_KEY}"},
                json={"prompt": prompt, "image_size": {"width": width, "height": height}, "num_images": 1},
            )
            r.raise_for_status()
            image_url = r.json()["images"][0]["url"]
            img_r = await client.get(image_url)
            img_r.raise_for_status()
            return img_r.content
    except Exception:
        return _placeholder(width, height)


def _placeholder(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(30, 41, 59))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
