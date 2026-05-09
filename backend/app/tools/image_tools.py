import asyncio
from io import BytesIO
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


async def apply_text_overlay(
    image_bytes: bytes,
    text_ar: str = "",
    text_en: str = "",
    arabic_font_url: str | None = None,
    config: dict | None = None,
) -> bytes:
    """Apply Arabic (gold, top) and English (white, bottom) text overlay with padding."""
    return await asyncio.to_thread(_apply_text_overlay_sync, image_bytes, text_ar, text_en)


def _apply_text_overlay_sync(image_bytes: bytes, text_ar: str, text_en: str) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    w, h = image.size
    pad = int(w * 0.1)  # 10% padding from edges

    font = ImageFont.load_default(size=max(24, w // 30))
    font_small = ImageFont.load_default(size=max(16, w // 45))

    # Semi-transparent overlay at bottom for readability
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([(0, h - int(h * 0.35)), (w, h)], fill=(10, 10, 10, 160))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Arabic copy — gold, near bottom (RTL)
    if text_ar:
        lines = wrap(text_ar, width=max(20, w // 20))[:3]
        y = h - int(h * 0.32)
        for line in lines:
            draw.text((w - pad, y), line, fill=(201, 168, 76), font=font, anchor="ra")
            y += font.size + 8

    # English copy — white, below Arabic
    if text_en:
        lines = wrap(text_en, width=max(30, w // 14))[:2]
        y = h - int(h * 0.12)
        for line in lines:
            draw.text((pad, y), line, fill=(248, 246, 241), font=font_small, anchor="la")
            y += font_small.size + 4

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


async def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    def _resize():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    return await asyncio.to_thread(_resize)


async def create_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    def _thumb():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    return await asyncio.to_thread(_thumb)
