"""
Template-driven creative renderer for Therapia marketing assets.

Architecture:
  1. fal.ai generates background/atmosphere ONLY (no text baked in)
  2. Pillow templates compose the final design with:
     - Arabic headline via Thmanyah Black font + arabic_reshaper + bidi
     - Brand colors, safe zones, CTA elements
     - Product showcase OR infographic layout

Two templates:
  render_product_showcase() — Variant A: headline + benefit + CTA + brand frame
  render_infographic()      — Variant B: metric hero + benefit blocks + headline

Arabic rules enforced:
  - Max 2 lines for headline, 1 line for subhead
  - Minimum font size 36px for readability
  - Right-aligned in dedicated text zone
  - No text rendered on top of faces or product details
"""
import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Fonts ──────────────────────────────────────────────────────────────────
_ASSETS = Path(__file__).parent.parent.parent / "assets" / "fonts" / "thmanyah typeface"
_SANS   = _ASSETS / "thmanyahsans" / "otf"

FONT_BLACK   = _SANS / "thmanyahsans-Black.otf"
FONT_BOLD    = _SANS / "thmanyahsans-Bold.otf"
FONT_MEDIUM  = _SANS / "thmanyahsans-Medium.otf"
FONT_REGULAR = _SANS / "thmanyahsans-Regular.otf"

_FONTS_LEGACY    = Path(__file__).parent.parent.parent / "fonts"
_FONT_BOLD_FB    = _FONTS_LEGACY / "thmanyah-bold.otf"
_FONT_REGULAR_FB = _FONTS_LEGACY / "thmanyah-regular.otf"

def _resolve(primary: Path, fallback: Path) -> Path:
    return primary if primary.exists() else fallback

FONT_BLACK   = _resolve(FONT_BLACK,   _FONT_BOLD_FB)
FONT_BOLD    = _resolve(FONT_BOLD,    _FONT_BOLD_FB)
FONT_MEDIUM  = _resolve(FONT_MEDIUM,  _FONT_BOLD_FB)
FONT_REGULAR = _resolve(FONT_REGULAR, _FONT_REGULAR_FB)


# ── Arabic text utilities ──────────────────────────────────────────────────

def _reshape_arabic(text: str) -> str:
    """
    Arabic for Pillow: get_display(reshape(text)) — words render connected.
    Non-connecting chars (ا, د, ر, و) at word boundaries may have minimal gap;
    acceptable for marketing copy. Use SHORT copy (3-5 words per line).
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default(size=size)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_arabic_lines(text: str, font: ImageFont.FreeTypeFont,
                        max_px: int, draw: ImageDraw.ImageDraw,
                        max_lines: int = 3) -> list[str]:
    """
    Reliable Arabic line-breaking:
    1. Work in LOGICAL (un-reshaped) Arabic text to preserve word integrity
    2. Build lines by adding whole words, measure the RESHAPED version for accuracy
    3. Each returned string is still in logical form — reshape at draw time
    """
    words = text.split()
    lines: list[str] = []
    current_words: list[str] = []

    for word in words:
        trial = current_words + [word]
        # Measure the line by reshaping the combined words left→right then bidi
        trial_text = " ".join(trial)
        trial_shaped = _reshape_arabic(trial_text)
        if _text_width(draw, trial_shaped, font) <= max_px:
            current_words = trial
        else:
            if current_words:
                lines.append(" ".join(current_words))
            current_words = [word]
        if len(lines) >= max_lines:
            break

    if current_words and len(lines) < max_lines:
        lines.append(" ".join(current_words))

    return lines[:max_lines]


def _draw_arabic_right(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    right_x: int,
    y: int,
    fill: tuple,
    max_width: int,
    line_spacing_ratio: float = 1.4,
) -> int:
    """Draw Arabic text, right-aligned, with proper reshape+bidi per line."""
    lines = _wrap_arabic_lines(text, font, max_width, draw)
    for line in lines:
        shaped = _reshape_arabic(line)
        w = _text_width(draw, shaped, font)
        x = right_x - w
        # Soft shadow
        draw.text((x + 2, y + 2), shaped, font=font, fill=(0, 0, 0, 90))
        draw.text((x, y), shaped, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        line_h = bbox[3] - bbox[1]
        y += int(line_h * line_spacing_ratio)
    return y


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore
    except Exception:
        return (10, 10, 10)


def _gradient_rect(img: Image.Image, x0: int, y0: int, x1: int, y1: int,
                    top_alpha: int, bottom_alpha: int, color: tuple[int,int,int]) -> None:
    """Draw a vertical gradient overlay rectangle."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    h = y1 - y0
    for dy in range(h):
        a = int(top_alpha + (bottom_alpha - top_alpha) * dy / max(h, 1))
        draw.line([(x0, y0 + dy), (x1, y0 + dy)], fill=(*color, a))
    img.alpha_composite(overlay)


# ── Template A: Product Showcase ──────────────────────────────────────────

def _render_product_showcase_sync(
    width: int, height: int,
    headline_ar: str,
    subhead_ar: str,
    cta_ar: str,
    cta_en: str,
    brand_primary: str,
    brand_accent: str,
    bg_bytes: bytes | None,
) -> bytes:
    primary_rgb = _hex_to_rgb(brand_primary)
    accent_rgb  = _hex_to_rgb(brand_accent)
    off_white   = (248, 246, 241)

    # ── Base canvas ──
    if bg_bytes:
        try:
            bg = Image.open(BytesIO(bg_bytes)).convert("RGBA")
            bg = bg.resize((width, height), Image.LANCZOS)
        except Exception:
            bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))
    else:
        bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))

    canvas = bg.copy()

    # ── Dark gradient overlay (bottom 65%) ──
    _gradient_rect(canvas, 0, int(height * 0.35), width, height,
                   top_alpha=0, bottom_alpha=230, color=(0, 0, 0))

    # ── Thin top brand bar ──
    draw = ImageDraw.Draw(canvas)
    bar_h = max(4, height // 200)
    draw.rectangle([(0, 0), (width, bar_h)], fill=(*accent_rgb, 255))

    pad = int(width * 0.07)
    right_edge = width - pad

    # ── Brand name top-left ──
    brand_font = _load_font(FONT_BOLD, max(18, width // 45))
    draw.text((pad, bar_h + int(height * 0.025)), "Therapia",
              font=brand_font, fill=(*accent_rgb, 255))

    # ── Arabic headline (max 2 lines, large) ──
    headline_size = max(46, width // 16)
    h_font = _load_font(FONT_BLACK, headline_size)
    h_y = int(height * 0.52)
    h_y = _draw_arabic_right(
        draw, headline_ar, h_font,
        right_x=right_edge, y=h_y,
        fill=off_white,
        max_width=int(width * 0.85),
    )

    # ── Arabic subheadline (1 line, smaller) ──
    if subhead_ar.strip():
        sub_size = max(28, width // 26)
        s_font = _load_font(FONT_BOLD, sub_size)
        h_y += int(height * 0.015)
        h_y = _draw_arabic_right(
            draw, subhead_ar, s_font,
            right_x=right_edge, y=h_y,
            fill=(*accent_rgb, 230),
            max_width=int(width * 0.75),
        )

    # ── CTA pill ──
    if cta_ar.strip() or cta_en.strip():
        cta_text = _reshape_arabic(cta_ar) if cta_ar.strip() else cta_en
        cta_size = max(22, width // 35)
        cta_font = _load_font(FONT_BOLD, cta_size)
        cta_w = _text_width(draw, cta_text, cta_font) + int(width * 0.06)
        cta_h = int(height * 0.06)
        cta_y = height - int(height * 0.1) - cta_h
        cta_x = right_edge - cta_w

        # Pill background
        draw.rounded_rectangle(
            [(cta_x, cta_y), (right_edge, cta_y + cta_h)],
            radius=cta_h // 2,
            fill=(*accent_rgb, 255),
        )
        # CTA text centered in pill
        draw.text(
            (cta_x + (cta_w - _text_width(draw, cta_text, cta_font)) // 2,
             cta_y + (cta_h - cta_size) // 2),
            cta_text, font=cta_font, fill=(255, 255, 255, 255),
        )

    # ── Accent bottom bar ──
    bar_bottom_h = max(6, height // 120)
    draw.rectangle([(0, height - bar_bottom_h), (width, height)],
                   fill=(*accent_rgb, 255))

    # ── Convert and return ──
    final = canvas.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


# ── Template B: Infographic / Outcome Campaign ─────────────────────────────

def _render_infographic_sync(
    width: int, height: int,
    headline_ar: str,
    benefits: list[str],
    metric_value: str,
    metric_label: str,
    cta_ar: str,
    cta_en: str,
    brand_primary: str,
    brand_accent: str,
    bg_bytes: bytes | None,
) -> bytes:
    primary_rgb = _hex_to_rgb(brand_primary)
    accent_rgb  = _hex_to_rgb(brand_accent)
    off_white   = (248, 246, 241)

    # ── Base canvas ──
    if bg_bytes:
        try:
            bg = Image.open(BytesIO(bg_bytes)).convert("RGBA")
            bg = bg.resize((width, height), Image.LANCZOS)
            # Soften the background for infographic readability
            from PIL import ImageFilter
            bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
        except Exception:
            bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))
    else:
        bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))

    canvas = bg.copy()

    # Strong overlay — infographic needs clean reading surface
    _gradient_rect(canvas, 0, 0, width, height,
                   top_alpha=200, bottom_alpha=240, color=primary_rgb)

    draw = ImageDraw.Draw(canvas)
    pad = int(width * 0.07)
    right_edge = width - pad

    # ── Top brand bar ──
    bar_h = max(4, height // 200)
    draw.rectangle([(0, 0), (width, bar_h)], fill=(*accent_rgb, 255))

    # ── Brand name ──
    brand_font = _load_font(FONT_BOLD, max(18, width // 45))
    draw.text((pad, bar_h + int(height * 0.025)), "Therapia",
              font=brand_font, fill=(*accent_rgb, 255))

    # ── Hero metric — number large, label smaller ──
    if metric_value.strip():
        num_size = max(110, width // 7)
        lbl_size = max(50, width // 14)
        num_font = _load_font(FONT_BLACK, num_size)
        lbl_font = _load_font(FONT_BOLD, lbl_size)

        num_w = _text_width(draw, metric_value, num_font)
        lbl_shaped = _reshape_arabic(metric_label) if metric_label else ""
        lbl_w = _text_width(draw, lbl_shaped, lbl_font) if lbl_shaped else 0

        m_y = int(height * 0.12)
        # Number centered
        num_x = (width - num_w) // 2
        draw.text((num_x + 3, m_y + 3), metric_value, font=num_font, fill=(0, 0, 0, 100))
        draw.text((num_x, m_y), metric_value, font=num_font, fill=(*accent_rgb, 255))

        # Label below number
        if lbl_shaped:
            lbl_x = (width - lbl_w) // 2
            lbl_y = m_y + num_size + int(height * 0.01)
            draw.text((lbl_x + 2, lbl_y + 2), lbl_shaped, font=lbl_font, fill=(0, 0, 0, 80))
            draw.text((lbl_x, lbl_y), lbl_shaped, font=lbl_font, fill=(*accent_rgb, 200))

    # ── Arabic headline ──
    h_size = max(38, width // 20)
    h_font = _load_font(FONT_BLACK, h_size)
    h_y = int(height * 0.42) if metric_value.strip() else int(height * 0.20)
    h_y = _draw_arabic_right(
        draw, headline_ar, h_font,
        right_x=right_edge, y=h_y,
        fill=off_white,
        max_width=int(width * 0.85),
    )

    # ── Benefit blocks (3 items, horizontal or stacked) ──
    if benefits:
        b_size = max(22, width // 38)
        b_font = _load_font(FONT_REGULAR, b_size)
        b_y = h_y + int(height * 0.04)
        block_h = int(height * 0.085)
        block_pad = int(width * 0.03)
        n = min(len(benefits), 3)
        block_w = (width - 2 * pad - (n - 1) * block_pad) // n

        for idx, benefit in enumerate(benefits[:n]):
            bx = pad + idx * (block_w + block_pad)
            by = b_y
            # Translucent block
            block_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(block_overlay)
            bd.rounded_rectangle(
                [(bx, by), (bx + block_w, by + block_h)],
                radius=max(6, block_h // 6),
                fill=(*accent_rgb, 35),
            )
            canvas.alpha_composite(block_overlay)
            draw = ImageDraw.Draw(canvas)

            # Benefit text — short, Arabic, centered in block
            b_shaped = _reshape_arabic(benefit[:20])  # hard cap per block
            bw = _text_width(draw, b_shaped, b_font)
            btext_x = bx + (block_w - bw) // 2
            btext_y = by + (block_h - b_size) // 2
            draw.text((btext_x, btext_y), b_shaped, font=b_font, fill=(*off_white, 220))

    # ── CTA ──
    if cta_ar.strip() or cta_en.strip():
        cta_text = _reshape_arabic(cta_ar) if cta_ar.strip() else cta_en
        cta_size = max(22, width // 35)
        cta_font = _load_font(FONT_BOLD, cta_size)
        cta_w = _text_width(draw, cta_text, cta_font) + int(width * 0.06)
        cta_h = int(height * 0.06)
        cta_y = height - int(height * 0.1) - cta_h
        cta_x = (width - cta_w) // 2
        draw.rounded_rectangle(
            [(cta_x, cta_y), (cta_x + cta_w, cta_y + cta_h)],
            radius=cta_h // 2,
            fill=(*accent_rgb, 255),
        )
        draw.text(
            (cta_x + (cta_w - _text_width(draw, cta_text, cta_font)) // 2,
             cta_y + (cta_h - cta_size) // 2),
            cta_text, font=cta_font, fill=(255, 255, 255, 255),
        )

    # ── Bottom bar ──
    bar_bottom_h = max(6, height // 120)
    draw.rectangle([(0, height - bar_bottom_h), (width, height)],
                   fill=(*accent_rgb, 255))

    final = canvas.convert("RGB")
    buf = BytesIO()
    final.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


# ── Public async wrappers ──────────────────────────────────────────────────

async def render_product_showcase(
    width: int, height: int,
    headline_ar: str,
    subhead_ar: str = "",
    cta_ar: str = "",
    cta_en: str = "",
    brand_primary: str = "#001A4D",
    brand_accent: str = "#4169E1",
    bg_bytes: bytes | None = None,
) -> bytes:
    """Variant A template — product showcase with controlled Arabic typography."""
    return await asyncio.to_thread(
        _render_product_showcase_sync,
        width, height, headline_ar, subhead_ar, cta_ar, cta_en,
        brand_primary, brand_accent, bg_bytes,
    )


async def render_infographic(
    width: int, height: int,
    headline_ar: str,
    benefits: list[str] | None = None,
    metric_value: str = "",
    metric_label: str = "",
    cta_ar: str = "",
    cta_en: str = "",
    brand_primary: str = "#001A4D",
    brand_accent: str = "#4169E1",
    bg_bytes: bytes | None = None,
) -> bytes:
    """Variant B template — infographic with metric hero + benefit blocks."""
    return await asyncio.to_thread(
        _render_infographic_sync,
        width, height, headline_ar, benefits or [], metric_value, metric_label,
        cta_ar, cta_en, brand_primary, brand_accent, bg_bytes,
    )


async def create_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    def _thumb():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    return await asyncio.to_thread(_thumb)


async def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    def _resize():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    return await asyncio.to_thread(_resize)


# ── Legacy: kept for compatibility but no longer used in main pipeline ──────

async def apply_text_overlay(
    image_bytes: bytes,
    text_ar: str = "",
    text_en: str = "",
    arabic_font_url: str | None = None,
    config: dict | None = None,
    brand_primary: str = "#0A0A0A",
    brand_accent: str = "#C9A84C",
) -> bytes:
    """Legacy overlay — replaced by render_product_showcase / render_infographic."""
    # Kept for backwards compatibility; just returns the image unchanged
    return image_bytes
