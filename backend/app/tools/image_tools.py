"""
Image tools — Layer 2 of the design pipeline.

Architecture (non-negotiable):
  Layer 1: fal.ai generates BEAUTIFUL VISUAL SCENE — no text, no Arabic
  Layer 2: Pillow overlays ALL text using Noto Naskh Arabic

Arabic rendering strategy — RAQM-aware:
  Railway Dockerfile builds Pillow with libraqm (HarfBuzz + FriBiDi).
  When RAQM is present, Pillow handles shaping + bidi internally.
  If we ALSO apply arabic_reshaper + bidi manually, the text gets double-reversed → "رمع".
  Fix: detect RAQM at startup. When available, pass raw Arabic + direction='rtl'.
  When not available (local dev without libraqm), use arabic_reshaper + bidi as fallback.
"""
import asyncio
import io
import os
from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features as pil_features

_FONT_BASE = Path(__file__).parent.parent.parent / "assets" / "fonts" / "thmanyah typeface" / "thmanyahsans" / "otf"
_NOTO_BASE = Path(__file__).parent.parent.parent / "assets" / "fonts" / "cairo"

# True when Pillow is built with libraqm — handles Arabic shaping natively
HAS_RAQM: bool = pil_features.check_feature("raqm")

# Noto Naskh Arabic — complete glyph coverage for both RAQM and non-RAQM paths
ARABIC_FONTS = {
    "black":   str(_NOTO_BASE / "NotoNaskhArabic-Bold.ttf"),
    "bold":    str(_NOTO_BASE / "NotoNaskhArabic-Bold.ttf"),
    "medium":  str(_NOTO_BASE / "NotoNaskhArabic-Regular.ttf"),
    "regular": str(_NOTO_BASE / "NotoNaskhArabic-Regular.ttf"),
    "light":   str(_NOTO_BASE / "NotoNaskhArabic-Regular.ttf"),
}

# Thmanyah — Latin/English text only
FONTS = {
    "black":   str(_FONT_BASE / "thmanyahsans-Black.otf"),
    "bold":    str(_FONT_BASE / "thmanyahsans-Bold.otf"),
    "medium":  str(_FONT_BASE / "thmanyahsans-Medium.otf"),
    "regular": str(_FONT_BASE / "thmanyahsans-Regular.otf"),
    "light":   str(_FONT_BASE / "thmanyahsans-Light.otf"),
}


def verify_fonts() -> dict:
    results = {"raqm_available": HAS_RAQM}
    for weight, path in {**FONTS, **{"ar_" + k: v for k, v in ARABIC_FONTS.items()}}.items():
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 48)
                results[weight] = "OK"
            except Exception as e:
                results[weight] = f"LOAD FAILED: {e}"
        else:
            results[weight] = f"MISSING: {path}"
    return results


def get_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Latin/English font (Thmanyah)."""
    path = FONTS.get(weight, FONTS["bold"])
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default(size=size)


def get_arabic_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """Arabic font — RAQM layout engine when available, standard otherwise."""
    path = ARABIC_FONTS.get(weight, ARABIC_FONTS["bold"])
    if os.path.exists(path):
        try:
            if HAS_RAQM:
                return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return get_font(weight, size)


def reshape_arabic(text: str) -> str:
    """Manual reshape — only used when RAQM is NOT available."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _arabic_text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    """Measure Arabic text width using the correct path for RAQM vs non-RAQM."""
    if HAS_RAQM:
        bbox = draw.textbbox((0, 0), text, font=font, direction="rtl", language="ar")
    else:
        bbox = draw.textbbox((0, 0), reshape_arabic(text), font=font)
    return bbox[2] - bbox[0]


def _draw_arabic(
    draw: ImageDraw.ImageDraw,
    right_x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
) -> None:
    """
    Draw Arabic text right-aligned at right_x.
    RAQM path: raw text + direction='rtl', anchor='ra' (right ascender).
    Non-RAQM path: manual reshape + bidi, draw from (right_x - width).
    """
    if HAS_RAQM:
        draw.text((right_x, y), text, font=font, fill=fill,
                  direction="rtl", language="ar", anchor="ra")
    else:
        shaped = reshape_arabic(text)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        lw = bbox[2] - bbox[0]
        draw.text((right_x - lw, y), shaped, font=font, fill=fill)


def wrap_arabic_text(text: str, font: ImageFont.FreeTypeFont, max_width: int,
                     draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        if _arabic_text_width(draw, test, font) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def add_text_shadow(draw: ImageDraw.ImageDraw, pos: tuple, text: str,
                    font: ImageFont.FreeTypeFont,
                    shadow_color=(0, 0, 0, 140), offset: int = 3) -> None:
    x, y = pos
    draw.text((x + offset, y + offset), text, font=font, fill=shadow_color)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore
    except Exception:
        return (76, 29, 149)  # default Therapia purple


def composite_final_image(
    background_bytes: bytes,
    copy_ar: str,
    copy_en: str,
    cta_ar: str,
    brand_colors: dict,
    logo_bytes: bytes | None = None,
    width: int = 1080,
    height: int = 1080,
) -> bytes:
    """
    Compose final marketing image:
    1. background_bytes from fal.ai (beautiful scene, NO text)
    2. Dark gradient overlay on bottom 50% for text legibility
    3. Brand accent bar top
    4. Arabic headline RIGHT-aligned via Thmanyah Black + arabic_reshaper
    5. CTA pill button
    6. Logo top-right (if available)
    7. Brand accent bar bottom
    """
    # Open background
    try:
        img = Image.open(BytesIO(background_bytes)).convert("RGBA")
        img = img.resize((width, height), Image.LANCZOS)
    except Exception:
        img = Image.new("RGBA", (width, height), (20, 10, 50, 255))

    primary_rgb = hex_to_rgb(brand_colors.get("primary", "#4C1D95"))
    accent_rgb  = hex_to_rgb(brand_colors.get("accent", "#F59E0B"))

    # ── 1. Dark gradient — bottom 50% ──────────────────────────────────────
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gradient)
    midpoint = height // 2
    for y in range(midpoint, height):
        alpha = int(190 * (y - midpoint) / (height - midpoint))
        gd.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, gradient)
    draw = ImageDraw.Draw(img)

    # ── 2. Brand accent bar — top 8px ──────────────────────────────────────
    draw.rectangle([(0, 0), (width, 8)], fill=(*primary_rgb, 255))

    padding = int(width * 0.07)
    right_edge = width - padding

    # ── 3. Logo top-right ──────────────────────────────────────────────────
    if logo_bytes:
        try:
            logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
            logo_max = int(width * 0.11)
            logo.thumbnail((logo_max, int(logo_max * 0.6)), Image.LANCZOS)
            lx = width - logo.width - padding
            ly = 14
            img.alpha_composite(logo, (lx, ly))
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # ── 4. Arabic headline — RIGHT aligned, Noto Naskh Arabic ─────────────
    headline_size = max(52, int(width * 0.060))
    headline_font = get_arabic_font("bold", headline_size)
    max_text_width = width - (padding * 2)

    ar_lines = wrap_arabic_text(copy_ar, headline_font, max_text_width, draw)
    ar_lines = ar_lines[:3]  # max 3 lines

    line_h = int(headline_size * 1.30)
    cta_h  = int(height * 0.075)
    cta_y  = height - padding - cta_h
    block_h = len(ar_lines) * line_h
    text_y  = cta_y - block_h - int(height * 0.03)

    for i, line in enumerate(ar_lines):
        y = text_y + i * line_h
        _draw_arabic(draw, right_edge, y, line, headline_font, (0, 0, 0, 160))  # shadow
        _draw_arabic(draw, right_edge - 2, y - 2, line, headline_font, (255, 255, 255, 255))

    # ── 5. English subhead (optional) ──────────────────────────────────────
    if copy_en.strip():
        sub_size = max(26, int(width * 0.028))
        sub_font = get_font("regular", sub_size)
        sub_text = copy_en[:90]
        sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        sub_x = right_edge - (sub_bbox[2] - sub_bbox[0])
        sub_y = text_y - sub_size - int(height * 0.015)
        draw.text((sub_x, sub_y), sub_text, font=sub_font, fill=(220, 215, 255, 200))

    # ── 6. CTA pill button ─────────────────────────────────────────────────
    if cta_ar.strip():
        cta_size = max(28, int(width * 0.033))
        cta_font = get_arabic_font("bold", cta_size)
        cta_tw = _arabic_text_width(draw, cta_ar, cta_font)
        pill_pad = int(width * 0.035)
        pill_w = cta_tw + pill_pad * 2
        pill_x = right_edge - pill_w
        draw.rounded_rectangle(
            [(pill_x, cta_y), (right_edge, cta_y + cta_h)],
            radius=cta_h // 2,
            fill=(*primary_rgb, 245),
        )
        cta_text_x = pill_x + pill_pad
        cta_text_y = cta_y + (cta_h - cta_size) // 2
        _draw_arabic(draw, cta_text_x + cta_tw, cta_text_y, cta_ar, cta_font, (255, 255, 255, 255))

    # ── 7. Brand accent bar — bottom 4px ───────────────────────────────────
    draw.rectangle([(0, height - 4), (width, height)], fill=(*accent_rgb, 220))

    # Save
    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="JPEG", quality=94, optimize=True)
    return buf.getvalue()


def composite_premium_arabic(
    background_bytes: bytes,
    copy_ar: str,
    copy_en: str,
    cta_ar: str,
    brand_colors: dict,
    logo_bytes: bytes | None = None,
    width: int = 1080,
    height: int = 1350,
    layout_pattern: str = "glass_card",
) -> bytes:
    """
    Premium Arabic compositing — replaces flat gradient approach.

    Layout patterns:
    - "glass_card": frosted glass panel at saliency-scored zone
    - "architectural_negative_space": text in detected low-saliency area, minimal treatment
    - "object_framed": text beside detected object boundary
    - "editorial_side": text right half, image left half
    - "centered_statement": single large headline, centered

    Text treatment: soft contact shadow + optional micro-stroke. NO heavy black gradient.
    """
    try:
        img = Image.open(BytesIO(background_bytes)).convert("RGBA")
        img = img.resize((width, height), Image.LANCZOS)
    except Exception:
        img = Image.new("RGBA", (width, height), (20, 10, 50, 255))

    primary_rgb = hex_to_rgb(brand_colors.get("primary", "#0F3D3E"))
    accent_rgb = hex_to_rgb(brand_colors.get("accent", "#D7B98E"))

    text_zone = _detect_text_zone(img, width, height, layout_pattern)

    if layout_pattern == "glass_card":
        img = _apply_glass_card(img, text_zone, width, height)
    elif layout_pattern == "architectural_negative_space":
        img = _apply_local_contrast_veil(img, text_zone, width, height)
    elif layout_pattern in ("editorial_side", "object_framed", "centered_statement"):
        img = _apply_soft_veil(img, text_zone, width, height)
    else:
        img = _apply_glass_card(img, text_zone, width, height)

    draw = ImageDraw.Draw(img)

    if logo_bytes:
        try:
            logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")
            logo_max = int(width * 0.11)
            logo.thumbnail((logo_max, int(logo_max * 0.6)), Image.LANCZOS)
            padding = int(width * 0.06)
            img.alpha_composite(logo, (width - logo.width - padding, 14))
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    draw.rectangle([(0, 0), (width, 4)], fill=(*primary_rgb, 200))

    tx, ty, tw, th_zone = text_zone
    padding_x = int(tw * 0.08)
    padding_y = int(th_zone * 0.10)

    headline_size = _calc_headline_size(copy_ar, width)
    headline_font = get_arabic_font("bold", headline_size)
    max_text_w = tw - padding_x * 2

    ar_lines = wrap_arabic_text(copy_ar, headline_font, max_text_w, draw)
    ar_lines = ar_lines[:2]

    line_h = int(headline_size * 1.08)
    block_h = len(ar_lines) * line_h

    text_start_y = ty + padding_y
    right_edge = tx + tw - padding_x

    for i, line in enumerate(ar_lines):
        y = text_start_y + i * line_h
        _draw_arabic(draw, right_edge, y + 4, line, headline_font, (0, 0, 0, 85))   # shadow
        _draw_arabic(draw, right_edge, y, line, headline_font, (255, 255, 255, 255))

    body_y = text_start_y + block_h + int(headline_size * 0.4)
    if copy_en.strip() and body_y < ty + th_zone - int(th_zone * 0.15):
        body_size = max(24, int(width * 0.026))
        body_font = get_font("regular", body_size)
        body_text = copy_en[:80]
        body_bbox = draw.textbbox((0, 0), body_text, font=body_font)
        bx = right_edge - (body_bbox[2] - body_bbox[0])
        draw.text((bx + 1, body_y + 2), body_text, font=body_font, fill=(0, 0, 0, 60))
        draw.text((bx, body_y), body_text, font=body_font, fill=(230, 225, 215, 210))

    if cta_ar.strip():
        cta_size = max(26, int(width * 0.030))
        cta_font = get_arabic_font("bold", cta_size)
        cta_tw_px = _arabic_text_width(draw, cta_ar, cta_font)
        pill_pad = int(width * 0.032)
        pill_w = cta_tw_px + pill_pad * 2
        pill_h = int(cta_size * 1.8)
        cta_zone_y = ty + th_zone - padding_y - pill_h
        pill_x = right_edge - pill_w
        draw.rounded_rectangle(
            [(pill_x, cta_zone_y), (right_edge, cta_zone_y + pill_h)],
            radius=pill_h // 2,
            fill=(*accent_rgb, 240),
        )
        cta_text_x = pill_x + pill_pad
        cta_text_y = cta_zone_y + (pill_h - cta_size) // 2
        _draw_arabic(draw, cta_text_x + cta_tw_px, cta_text_y, cta_ar, cta_font, (20, 20, 20, 255))

    final = img.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue()


def _detect_text_zone(img: Image.Image, width: int, height: int, pattern: str) -> tuple:
    """
    Returns (x, y, w, h) for text placement zone.
    Simple saliency proxy: find quadrant with lowest mean brightness.
    Real implementation: OpenCV saliency + edge density map.
    """
    import numpy as np

    arr = np.array(img.convert("L"))

    mid_x, mid_y = width // 2, height // 2
    quads = {
        "upper_right": arr[:mid_y, mid_x:].mean(),
        "upper_left": arr[:mid_y, :mid_x].mean(),
        "lower_right": arr[mid_y:, mid_x:].mean(),
        "lower_left": arr[mid_y:, :mid_x].mean(),
    }

    if pattern == "editorial_side":
        return (mid_x, int(height * 0.20), mid_x, int(height * 0.60))
    if pattern == "centered_statement":
        padding = int(width * 0.08)
        return (padding, int(height * 0.30), width - padding * 2, int(height * 0.40))

    best = min(quads, key=quads.get)
    margin = int(width * 0.06)
    if best == "upper_right":
        return (mid_x + margin, margin, mid_x - margin * 2, int(height * 0.45))
    if best == "upper_left":
        return (margin, margin, mid_x - margin * 2, int(height * 0.45))
    if best == "lower_right":
        return (mid_x + margin, mid_y, mid_x - margin * 2, int(height * 0.45))
    return (margin, mid_y, mid_x - margin * 2, int(height * 0.45))


def _apply_glass_card(img: Image.Image, zone: tuple, width: int, height: int) -> Image.Image:
    """Frosted glass panel behind text zone. Premium look."""
    x, y, w, h = zone
    region = img.crop((x, y, x + w, y + h))
    blurred = region.filter(ImageFilter.GaussianBlur(20))
    img.paste(blurred, (x, y))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    panel = Image.new("RGBA", (w, h), (12, 18, 20, 105))
    overlay.paste(panel, (x, y))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    draw.rectangle([(x, y), (x + w, y + h)], outline=(255, 255, 255, 35), width=1)
    return img


def _apply_local_contrast_veil(img: Image.Image, zone: tuple, width: int, height: int) -> Image.Image:
    """Subtle gradient only behind text zone. Not full-image gradient."""
    x, y, w, h = zone
    veil = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for dy in range(h):
        alpha = int(55 * dy / h)
        vd.line([(x, y + dy), (x + w, y + dy)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img, veil)


def _apply_soft_veil(img: Image.Image, zone: tuple, width: int, height: int) -> Image.Image:
    """Minimal treatment for architectural/editorial patterns."""
    x, y, w, h = zone
    veil = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    vd.rectangle([(x, y), (x + w, y + h)], fill=(0, 0, 0, 35))
    return Image.alpha_composite(img, veil)


def _calc_headline_size(text: str, width: int) -> int:
    """Scale headline based on text length. Short = big. Long = smaller."""
    word_count = len(text.split())
    if word_count <= 4:
        return max(72, int(width * 0.075))
    if word_count <= 7:
        return max(60, int(width * 0.062))
    return max(52, int(width * 0.050))


async def create_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    def _t() -> bytes:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    return await asyncio.to_thread(_t)


async def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    def _r() -> bytes:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    return await asyncio.to_thread(_r)


# ── Legacy compat ─────────────────────────────────────────────────────────────
async def apply_text_overlay(image_bytes: bytes, *args, **kwargs) -> bytes:
    return image_bytes

async def render_product_showcase(
    width: int, height: int,
    headline_ar: str = "",
    subhead_ar: str = "",
    cta_ar: str = "",
    cta_en: str = "",
    brand_primary: str = "#4C1D95",
    brand_accent: str = "#F59E0B",
    bg_bytes: bytes | None = None,
    logo_bytes: bytes | None = None,
) -> bytes:
    return await asyncio.to_thread(
        composite_final_image,
        bg_bytes or b"",
        headline_ar,
        cta_en or subhead_ar,
        cta_ar,
        {"primary": brand_primary, "accent": brand_accent},
        logo_bytes,
        width,
        height,
    )

async def render_infographic(
    width: int, height: int,
    headline_ar: str = "",
    benefits: list | None = None,
    metric_value: str = "",
    metric_label: str = "",
    cta_ar: str = "",
    cta_en: str = "",
    brand_primary: str = "#4C1D95",
    brand_accent: str = "#F59E0B",
    bg_bytes: bytes | None = None,
    logo_bytes: bytes | None = None,
) -> bytes:
    # For infographics, prepend metric to headline if available
    full_ar = headline_ar
    if metric_value and metric_label:
        full_ar = f"{metric_value} {metric_label} — {headline_ar}" if headline_ar else f"{metric_value} {metric_label}"
    return await asyncio.to_thread(
        composite_final_image,
        bg_bytes or b"",
        full_ar,
        cta_en,
        cta_ar,
        {"primary": brand_primary, "accent": brand_accent},
        logo_bytes,
        width,
        height,
    )
