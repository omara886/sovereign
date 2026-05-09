from PIL import Image
from io import BytesIO


async def generate_image_fal(prompt: str, model: str, width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), color=(30, 41, 59))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
