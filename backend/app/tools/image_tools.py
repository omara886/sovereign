"""
Image tools — branded social media card generator.
Thmanyah typeface family — Black for headlines, Bold for subheads, Regular for body.
Arabic text: reshaped + bidi for correct RTL connected-letter rendering.
open-codesign spacing: 8pt grid, generous breathing room, warm dark background.
"""
import asyncio
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

# Thmanyah typeface — production font paths
_ASSETS = Path(__file__).parent.parent.parent / "assets" / "fonts" / "thmanyah typeface"
_SANS   = _ASSETS / "thmanyahsans" / "otf"
_SERIF  = _ASSETS / "thmanyahserifdisplay" / "otf"

# Weight hierarchy: Black=headline, Bold=subhead, Medium=label, Regular=body
FONT_BLACK   = _SANS  / "thmanyahsans-Black.otf"
FONT_BOLD    = _SANS  / "thmanyahsans-Bold.otf"
FONT_MEDIUM  = _SANS  / "thmanyahsans-Medium.otf"
FONT_REGULAR = _SANS  / "thmanyahsans-Regular.otf"
FONT_SERIF_BOLD = _SERIF / "thmanyahserifdisplay-Bold.otf"

# Fallback copies (legacy, kept for safety)
_FONTS_LEGACY = Path(__file__).parent.parent.parent / "fonts"
_FONT_BOLD_FB    = _FONTS_LEGACY / "thmanyah-bold.otf"
_FONT_REGULAR_FB = _FONTS_LEGACY / "thmanyah-regular.otf"

# Resolve with fallback
def _resolve(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback

FONT_BLACK   = _resolve(FONT_BLACK,   _FONT_BOLD_FB)
FONT_BOLD    = _resolve(FONT_BOLD,    _FONT_BOLD_FB)
FONT_MEDIUM  = _resolve(FONT_MEDIUM,  _FONT_BOLD_FB)
FONT_REGULAR = _resolve(FONT_REGULAR, _FONT_REGULAR_FB)


def _reshape_arabic(text: str) -> str:
    """Reshape + apply bidi so Arabic renders correctly in Pillow (RTL, connected letters)."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default(size=size)


def _draw_text_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
    fill: tuple,
    align: str = "left",
    line_spacing: int = 8,
    is_arabic: bool = False,
) -> int:
    """Draw wrapped text and return the Y position after last line."""
    if is_arabic:
        text = _reshape_arabic(text)

    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip() if current else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        if align == "center":
            lx = x - w // 2
        elif align == "right":
            lx = x - w
        else:
            lx = x
        draw.text((lx, y), line, font=font, fill=fill)
        y += (bbox[3] - bbox[1]) + line_spacing

    return y


def _make_branded_image(
    width: int,
    height: int,
    text_ar: str,
    text_en: str,
    brand_primary: str = "#0A0A0A",
    brand_accent: str = "#C9A84C",
) -> bytes:
    """
    Generate a branded social media card with:
    - Dark gradient background
    - Gold accent stripe at bottom
    - Arabic text (Thmanyah Bold, gold) in upper section
    - English text (Thmanyah Regular, white) below Arabic
    - Decorative gold line separator
    """
    def hex_to_rgb(h: str) -> tuple:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    primary_rgb = hex_to_rgb(brand_primary) if brand_primary.startswith("#") else (10, 10, 10)
    accent_rgb  = hex_to_rgb(brand_accent)  if brand_accent.startswith("#")  else (201, 168, 76)

    # Base background — vertical gradient from slate to obsidian
    img = Image.new("RGB", (width, height), primary_rgb)
    draw = ImageDraw.Draw(img)

    # Gradient: top = slate (#1E293B), bottom = obsidian
    top_color    = (30, 41, 59)   # #1E293B
    bottom_color = primary_rgb
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Gold accent: thin stripe at very bottom
    stripe_h = max(6, height // 120)
    draw.rectangle([(0, height - stripe_h), (width, height)], fill=accent_rgb)

    # Subtle gold gradient at bottom-left corner
    for i in range(height // 5):
        alpha = int(80 * (1 - i / (height / 5)))
        r = int(accent_rgb[0] * alpha / 255)
        g = int(accent_rgb[1] * alpha / 255)
        b = int(accent_rgb[2] * alpha / 255)
        draw.line([(0, height - stripe_h - i), (width // 4, height - stripe_h - i)], fill=(r, g, b))

    pad = int(width * 0.08)
    center_x = width // 2
    text_max_w = width - pad * 2

    # Thmanyah weight hierarchy + open-codesign type scale ratios
    # display-2xl(48px) / body-lg(17px) = 2.8x — same ratio in image
    ar_size    = max(44, width // 16)   # Black — headline, dominant
    en_size    = max(24, width // 28)   # Regular — body, secondary
    label_size = max(14, width // 55)   # Medium — label/watermark

    font_ar    = _load_font(FONT_BLACK,   ar_size)    # Thmanyah Black — headlines
    font_en    = _load_font(FONT_REGULAR, en_size)    # Thmanyah Regular — body
    font_label = _load_font(FONT_MEDIUM,  label_size) # Thmanyah Medium — labels

    # Layout: start Arabic text at ~30% from top
    y = int(height * 0.28)

    # Arabic text — gold, centered, RTL
    if text_ar:
        ar_color = accent_rgb
        # Draw subtle glow behind Arabic text
        y = _draw_text_wrapped(
            draw, text_ar, font_ar,
            x=center_x, y=y,
            max_width=text_max_w,
            fill=ar_color,
            align="center",
            line_spacing=max(10, ar_size // 4),
            is_arabic=True,
        )
        y += int(height * 0.03)

    # Gold separator line
    if text_ar and text_en:
        line_y = y + int(height * 0.01)
        line_w = min(text_max_w // 3, 200)
        draw.rectangle(
            [(center_x - line_w // 2, line_y), (center_x + line_w // 2, line_y + 2)],
            fill=(*accent_rgb, 120)
        )
        y = line_y + int(height * 0.04)

    # English text — off-white, centered
    if text_en:
        en_color = (220, 218, 213)  # off-white
        y = _draw_text_wrapped(
            draw, text_en, font_en,
            x=center_x, y=y,
            max_width=text_max_w,
            fill=en_color,
            align="center",
            line_spacing=max(8, en_size // 5),
            is_arabic=False,
        )

    # Watermark — "Powered by Sovereign" bottom-left, very small
    wm = _load_font(FONT_REGULAR, max(12, width // 80))
    draw.text((pad, height - stripe_h - max(20, height // 50) - 4), "SOVEREIGN", font=wm, fill=(*accent_rgb, 80))

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def apply_text_overlay(
    image_bytes: bytes,
    text_ar: str = "",
    text_en: str = "",
    arabic_font_url: str | None = None,
    config: dict | None = None,
    brand_primary: str = "#0A0A0A",
    brand_accent: str = "#C9A84C",
) -> bytes:
    """
    If fal.ai returned a real image: overlay text on it.
    If fal.ai returned a placeholder (solid color): replace with branded card.
    """
    def _process():
        try:
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception:
            img = None

        # Detect placeholder: if image is essentially monochromatic (solid dark)
        is_placeholder = False
        if img:
            # Sample 9 pixels across image — if variance < threshold it's a placeholder
            w, h = img.size
            samples = [img.getpixel((w * x // 4, h * y // 4)) for x in range(1, 4) for y in range(1, 4)]
            r_vals = [s[0] for s in samples]
            g_vals = [s[1] for s in samples]
            b_vals = [s[2] for s in samples]
            variance = max(max(r_vals) - min(r_vals), max(g_vals) - min(g_vals), max(b_vals) - min(b_vals))
            is_placeholder = variance < 15  # near-solid color

        if is_placeholder or not img:
            # Replace placeholder with proper branded design
            width = img.size[0] if img else 1080
            height = img.size[1] if img else 1080
            return _make_branded_image(width, height, text_ar, text_en, brand_primary, brand_accent)

        # Real fal.ai image — overlay text on it
        w, h = img.size
        draw = ImageDraw.Draw(img)
        pad = int(w * 0.06)
        center_x = w // 2
        text_max_w = w - pad * 2

        accent_rgb = (201, 168, 76)
        # Thmanyah weight hierarchy on real fal.ai images
        ar_size = max(38, w // 17)   # Black for Arabic headline
        en_size = max(22, w // 30)   # Regular for English body
        font_ar = _load_font(FONT_BLACK,   ar_size)   # Thmanyah Black — max impact
        font_en = _load_font(FONT_REGULAR, en_size)   # Thmanyah Regular — clean body

        # Semi-transparent overlay at bottom 40% for text readability
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        overlay_top = int(h * 0.6)
        for i, y_pos in enumerate(range(overlay_top, h)):
            alpha = int(200 * (y_pos - overlay_top) / (h - overlay_top))
            ov_draw.line([(0, y_pos), (w, y_pos)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        y = int(h * 0.62)
        if text_ar:
            y = _draw_text_wrapped(draw, text_ar, font_ar, center_x, y, text_max_w, accent_rgb, "center", is_arabic=True)
            y += 8
        if text_en:
            _draw_text_wrapped(draw, text_en, font_en, center_x, y, text_max_w, (220, 218, 213), "center")

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    return await asyncio.to_thread(_process)


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
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    return await asyncio.to_thread(_thumb)
