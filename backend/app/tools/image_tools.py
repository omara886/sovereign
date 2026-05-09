from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def apply_text_overlay(image_bytes: bytes, text_ar: str, text_en: str, arabic_font_url: str, config: dict) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((40, 40), text_en or "", fill=(248, 246, 241), font=font)
    draw.text((40, 90), text_ar or "", fill=(201, 168, 76), font=font)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((width, height))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def create_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((max_size, max_size))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
