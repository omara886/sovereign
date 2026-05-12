"""
Template-driven creative renderer for Therapia marketing assets.

Arabic rendering strategy:
  PREFERRED  — Pillow + libraqm + HarfBuzz + FriBiDi
               ImageFont.Layout.RAQM + direction='rtl' + language='ar'
               Full OpenType shaping, correct joining, correct BiDi ordering.

  FALLBACK   — arabic_reshaper + python-bidi + Pillow basic layout
               Used only when libraqm is unavailable (detected at startup).
               DO NOT combine both paths — RAQM already handles shaping+bidi.

  NEVER      — Ask fal.ai to render Arabic text.

Two templates:
  render_product_showcase() — Variant A
  render_infographic()      — Variant B

Brand colors: all final text/CTA/pill/stat colors come from brand_memory,
never hardcoded. Tokens: accent, primary (background), text=off-white on dark.
"""
import asyncio
import logging
import warnings
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

logger = logging.getLogger(__name__)

# ── RAQM detection (done once at import) ──────────────────────────────────────
_RAQM_AVAILABLE: bool = features.check("raqm")

if _RAQM_AVAILABLE:
    logger.info("image_tools: RAQM available — using HarfBuzz shaping + FriBiDi RTL")
else:
    logger.warning(
        "image_tools: RAQM NOT available — using arabic_reshaper+python-bidi fallback. "
        "Install libraqm + rebuild Pillow from source for production-grade Arabic."
    )

# ── Fonts ──────────────────────────────────────────────────────────────────────
_ASSETS = Path(__file__).parent.parent.parent / "assets" / "fonts" / "thmanyah typeface"
_SANS   = _ASSETS / "thmanyahsans" / "otf"

_FONT_BLACK_PATH   = _SANS / "thmanyahsans-Black.otf"
_FONT_BOLD_PATH    = _SANS / "thmanyahsans-Bold.otf"
_FONT_REGULAR_PATH = _SANS / "thmanyahsans-Regular.otf"

_FONTS_LEGACY = Path(__file__).parent.parent.parent / "fonts"
_FB_BOLD    = _FONTS_LEGACY / "thmanyah-bold.otf"
_FB_REGULAR = _FONTS_LEGACY / "thmanyah-regular.otf"

def _resolve(p: Path, fb: Path) -> Path:
    return p if p.exists() else fb

FONT_BLACK_PATH   = _resolve(_FONT_BLACK_PATH,   _FB_BOLD)
FONT_BOLD_PATH    = _resolve(_FONT_BOLD_PATH,     _FB_BOLD)
FONT_REGULAR_PATH = _resolve(_FONT_REGULAR_PATH,  _FB_REGULAR)


# ── Font loader: RAQM-preferred ───────────────────────────────────────────────

def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    """Load font with RAQM layout engine when available."""
    try:
        if _RAQM_AVAILABLE:
            return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
        return ImageFont.truetype(str(path), size)
    except Exception:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ImageFont.load_default(size=size)


# ── Arabic text rendering ──────────────────────────────────────────────────────

def _prepare_arabic(text: str) -> str:
    """
    RAQM path: return text unchanged — RAQM/HarfBuzz handles shaping+BiDi internally.
    Fallback path: apply arabic_reshaper + python-bidi.
    NEVER combine both — RAQM and reshaper conflict.
    """
    if _RAQM_AVAILABLE:
        return text  # RAQM does shaping and RTL ordering itself
    # Fallback only
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text), base_dir="R")
    except Exception:
        return text


def _draw_arabic_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    fill: tuple,
    anchor: str = "ra",  # right-aligned anchor
) -> None:
    """Draw Arabic text with correct shaping and shadow."""
    display_text = _prepare_arabic(text)
    kwargs: dict = {"font": font, "fill": fill}
    if _RAQM_AVAILABLE:
        kwargs["direction"] = "rtl"
        kwargs["language"]  = "ar"
        kwargs["anchor"]    = anchor  # "ra" = right-ascender, right-aligned
    else:
        # Fallback: draw from right edge manually (text already pre-reversed by bidi)
        try:
            bb = draw.textbbox((0, 0), display_text, font=font)
            w = bb[2] - bb[0]
            x = x - w  # shift left so right edge aligns
        except Exception:
            pass
        kwargs.pop("anchor", None)

    # Shadow
    shadow_fill = (0, 0, 0, 80)
    try:
        draw.text((x + 2, y + 2), display_text, fill=shadow_fill, font=font,
                  **({"direction": "rtl", "language": "ar", "anchor": anchor}
                     if _RAQM_AVAILABLE else {}))
    except Exception:
        pass
    draw.text((x, y), display_text, **kwargs)


def _arabic_text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> int:
    """Measure Arabic text width using the active render path."""
    display_text = _prepare_arabic(text)
    try:
        if _RAQM_AVAILABLE:
            bb = draw.textbbox((0, 0), display_text, font=font, direction="rtl", language="ar")
        else:
            bb = draw.textbbox((0, 0), display_text, font=font)
        return bb[2] - bb[0]
    except Exception:
        return len(text) * (font.size // 2)


def _wrap_arabic(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_px: int,
    draw: ImageDraw.ImageDraw,
    max_lines: int = 2,
) -> list[str]:
    """
    Word-wrap Arabic. Measure after shaping (width changes with joining forms).
    Returns list of LOGICAL strings; _draw_arabic_text shapes each line at draw time.
    """
    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    for word in words:
        trial = current + [word]
        trial_str = " ".join(trial)
        w = _arabic_text_width(draw, trial_str, font)
        if w <= max_px:
            current = trial
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
        if len(lines) >= max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(" ".join(current))

    return lines[:max_lines]


# ── Color utils ────────────────────────────────────────────────────────────────

def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore
    except Exception:
        return (0, 26, 77)


def _gradient_rect(
    img: Image.Image, x0: int, y0: int, x1: int, y1: int,
    top_alpha: int, bottom_alpha: int, color: tuple[int, int, int]
) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    h = y1 - y0
    for dy in range(h):
        a = int(top_alpha + (bottom_alpha - top_alpha) * dy / max(h, 1))
        d.line([(x0, y0 + dy), (x1, y0 + dy)], fill=(*color, a))
    img.alpha_composite(overlay)


# ── Template A: Product Showcase ───────────────────────────────────────────────

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
    # Brand tokens — all from brand_memory, no hardcoded fallbacks
    primary_rgb = _hex(brand_primary)
    accent_rgb  = _hex(brand_accent)
    text_on_dark = (248, 246, 241)    # off-white headline on dark bg
    text_on_accent = (255, 255, 255)  # white text on accent pill

    # ── Canvas ──
    if bg_bytes:
        try:
            bg = Image.open(BytesIO(bg_bytes)).convert("RGBA")
            bg = bg.resize((width, height), Image.LANCZOS)
        except Exception:
            bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))
    else:
        bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))

    canvas = bg.copy()

    # ── Dark gradient bottom 65% ──
    _gradient_rect(canvas, 0, int(height * 0.35), width, height,
                   top_alpha=0, bottom_alpha=235, color=(0, 0, 0))

    draw = ImageDraw.Draw(canvas)
    pad = int(width * 0.07)
    right_edge = width - pad

    # ── Top accent bar ──
    draw.rectangle([(0, 0), (width, max(4, height // 200))],
                   fill=(*accent_rgb, 255))

    # ── Brand name top-left ──
    brand_font = _load_font(FONT_BOLD_PATH, max(18, width // 45))
    draw.text((pad, max(4, height // 200) + int(height * 0.02)),
              "Therapia", font=brand_font, fill=(*accent_rgb, 255))

    # ── Arabic headline — anchored right, max 2 lines ──
    h_size = max(48, width // 15)
    h_font = _load_font(FONT_BLACK_PATH, h_size)
    headline_y = int(height * 0.52)
    lines = _wrap_arabic(headline_ar, h_font, int(width * 0.84), draw, max_lines=2)
    for line in lines:
        _draw_arabic_text(draw, line, h_font, right_edge, headline_y, text_on_dark)
        try:
            bb = draw.textbbox((0, 0), _prepare_arabic(line), font=h_font,
                               **({"direction":"rtl","language":"ar"} if _RAQM_AVAILABLE else {}))
            headline_y += int((bb[3] - bb[1]) * 1.35)
        except Exception:
            headline_y += int(h_size * 1.35)

    # ── Arabic subhead — 1 line ──
    if subhead_ar.strip():
        s_size = max(28, width // 26)
        s_font = _load_font(FONT_BOLD_PATH, s_size)
        headline_y += int(height * 0.015)
        _draw_arabic_text(draw, subhead_ar[:50], s_font, right_edge, headline_y,
                          (*accent_rgb, 210))

    # ── CTA pill (accent background, white text) ──
    cta_text = cta_ar.strip() or cta_en.strip()
    if cta_text:
        cta_size = max(22, width // 35)
        cta_font = _load_font(FONT_BOLD_PATH, cta_size)
        cta_w = _arabic_text_width(draw, cta_text, cta_font) + int(width * 0.07)
        cta_h = int(height * 0.065)
        cta_y = height - int(height * 0.09) - cta_h
        cta_x = right_edge - cta_w
        draw.rounded_rectangle([(cta_x, cta_y), (right_edge, cta_y + cta_h)],
                                radius=cta_h // 2, fill=(*accent_rgb, 255))
        pill_center_x = cta_x + cta_w // 2
        _draw_arabic_text(draw, cta_text, cta_font,
                          pill_center_x + _arabic_text_width(draw, cta_text, cta_font) // 2,
                          cta_y + (cta_h - cta_size) // 2,
                          text_on_accent)

    # ── Bottom accent bar ──
    draw.rectangle([(0, height - max(6, height // 120)), (width, height)],
                   fill=(*accent_rgb, 255))

    buf = BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


# ── Template B: Infographic ────────────────────────────────────────────────────

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
    primary_rgb  = _hex(brand_primary)
    accent_rgb   = _hex(brand_accent)
    text_on_dark = (248, 246, 241)
    text_on_accent = (255, 255, 255)

    if bg_bytes:
        try:
            from PIL import ImageFilter
            bg = Image.open(BytesIO(bg_bytes)).convert("RGBA")
            bg = bg.resize((width, height), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=6))
        except Exception:
            bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))
    else:
        bg = Image.new("RGBA", (width, height), (*primary_rgb, 255))

    canvas = bg.copy()
    _gradient_rect(canvas, 0, 0, width, height,
                   top_alpha=190, bottom_alpha=240, color=primary_rgb)

    draw = ImageDraw.Draw(canvas)
    pad = int(width * 0.07)
    right_edge = width - pad

    # ── Top accent bar + brand name ──
    draw.rectangle([(0, 0), (width, max(4, height // 200))],
                   fill=(*accent_rgb, 255))
    brand_font = _load_font(FONT_BOLD_PATH, max(18, width // 45))
    draw.text((pad, max(4, height // 200) + int(height * 0.02)),
              "Therapia", font=brand_font, fill=(*accent_rgb, 255))

    # ── Hero metric: number + label separately ──
    if metric_value.strip():
        num_size = max(120, width // 6)
        lbl_size = max(52, width // 13)
        num_font = _load_font(FONT_BLACK_PATH, num_size)
        lbl_font = _load_font(FONT_BOLD_PATH,  lbl_size)

        # Number centered
        num_w = _arabic_text_width(draw, metric_value, num_font)
        num_x = (width + num_w) // 2  # right anchor for centered effect
        draw.text((num_x + 3, int(height * 0.13) + 3), metric_value,
                  font=num_font, fill=(0, 0, 0, 100))
        draw.text((num_x, int(height * 0.13)), metric_value,
                  font=num_font, fill=(*accent_rgb, 255))

        # Label below
        if metric_label.strip():
            lbl_x = (width + _arabic_text_width(draw, metric_label, lbl_font)) // 2
            lbl_y = int(height * 0.13) + num_size + int(height * 0.01)
            _draw_arabic_text(draw, metric_label, lbl_font, lbl_x, lbl_y,
                              (*accent_rgb, 190))

    # ── Arabic headline ──
    h_size = max(40, width // 20)
    h_font = _load_font(FONT_BLACK_PATH, h_size)
    h_y = int(height * 0.44) if metric_value.strip() else int(height * 0.20)
    lines = _wrap_arabic(headline_ar, h_font, int(width * 0.84), draw, max_lines=2)
    for line in lines:
        _draw_arabic_text(draw, line, h_font, right_edge, h_y, text_on_dark)
        try:
            bb = draw.textbbox((0, 0), _prepare_arabic(line), font=h_font,
                               **({"direction":"rtl","language":"ar"} if _RAQM_AVAILABLE else {}))
            h_y += int((bb[3] - bb[1]) * 1.35)
        except Exception:
            h_y += int(h_size * 1.35)

    # ── Benefit blocks ──
    if benefits:
        b_size = max(22, width // 38)
        b_font = _load_font(FONT_REGULAR_PATH, b_size)
        b_y = h_y + int(height * 0.04)
        block_pad = int(width * 0.025)
        n = min(len(benefits), 3)
        block_w = (width - 2 * pad - (n - 1) * block_pad) // n
        block_h = int(height * 0.088)

        for idx, benefit in enumerate(benefits[:n]):
            bx = pad + idx * (block_w + block_pad)
            block_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            bd = ImageDraw.Draw(block_overlay)
            bd.rounded_rectangle([(bx, b_y), (bx + block_w, b_y + block_h)],
                                  radius=max(8, block_h // 6),
                                  fill=(*accent_rgb, 30))
            canvas.alpha_composite(block_overlay)
            draw = ImageDraw.Draw(canvas)

            bw = _arabic_text_width(draw, benefit[:18], b_font)
            _draw_arabic_text(draw, benefit[:18], b_font,
                              bx + (block_w + bw) // 2,
                              b_y + (block_h - b_size) // 2,
                              (*text_on_dark, 220))

    # ── CTA pill ──
    cta_text = cta_ar.strip() or cta_en.strip()
    if cta_text:
        cta_size = max(22, width // 35)
        cta_font = _load_font(FONT_BOLD_PATH, cta_size)
        cta_w = _arabic_text_width(draw, cta_text, cta_font) + int(width * 0.07)
        cta_h = int(height * 0.065)
        cta_y = height - int(height * 0.09) - cta_h
        cta_x = (width - cta_w) // 2
        draw.rounded_rectangle([(cta_x, cta_y), (cta_x + cta_w, cta_y + cta_h)],
                                radius=cta_h // 2, fill=(*accent_rgb, 255))
        _draw_arabic_text(draw, cta_text, cta_font,
                          cta_x + (cta_w + _arabic_text_width(draw, cta_text, cta_font)) // 2,
                          cta_y + (cta_h - cta_size) // 2, text_on_accent)

    # ── Bottom bar ──
    draw.rectangle([(0, height - max(6, height // 120)), (width, height)],
                   fill=(*accent_rgb, 255))

    buf = BytesIO()
    canvas.convert("RGB").save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


# ── Public async API ───────────────────────────────────────────────────────────

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
    return await asyncio.to_thread(
        _render_infographic_sync,
        width, height, headline_ar, benefits or [], metric_value, metric_label,
        cta_ar, cta_en, brand_primary, brand_accent, bg_bytes,
    )


async def create_thumbnail(image_bytes: bytes, max_size: int = 400) -> bytes:
    def _t():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()
    return await asyncio.to_thread(_t)


async def resize_image(image_bytes: bytes, width: int, height: int) -> bytes:
    def _r():
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img = img.resize((width, height), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    return await asyncio.to_thread(_r)


# ── Legacy compat (no-op) ──────────────────────────────────────────────────────
async def apply_text_overlay(image_bytes: bytes, *args, **kwargs) -> bytes:
    return image_bytes
