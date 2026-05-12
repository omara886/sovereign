"""
Open Design Adapter — Variant C design engine.

Uses the local Open Design daemon (http://127.0.0.1:58846) to generate
an HTML artifact, then screenshots it to produce a thumbnail.

API flow:
  POST /api/artifacts/save  { identifier, title, html }
  → { url: '/artifacts/{slug}/index.html', path, lint[] }

The daemon serves the artifact at GET {DAEMON_URL}/artifacts/{slug}/index.html.
We screenshot it with Playwright (if available) or Pillow HTML renderer.

Enabled only when OPEN_DESIGN_ENABLED=true in env.
Does NOT break existing fal.ai flow when disabled.
"""
import asyncio
import hashlib
import json
import logging
from io import BytesIO

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Open CoDesign principles applied in this adapter
OPENCODESIGN_PRINCIPLES = [
    "open-design daemon: HTML artifact engine, not a raw prompt",
    "Brand-controlled: colors and copy from brand_memory, not freeform",
    "Layout: CSS grid/flex, 8pt spacing, safe-area text zones",
    "Arabic: rendered as HTML text node with dir=rtl (browser handles BiDi natively)",
    "Thumbnail: Playwright screenshot or Pillow HTML fallback",
]


def _build_html(
    headline_ar: str,
    subhead_ar: str,
    cta_ar: str,
    cta_en: str,
    brand_primary: str,
    brand_accent: str,
    width: int,
    height: int,
    project_name: str = "Therapia",
) -> str:
    """
    Build a brand-controlled HTML card.
    Arabic rendered as HTML text with dir=rtl — browser handles shaping natively.
    No arabic_reshaper needed here.
    """
    pad = max(48, int(width * 0.07))
    h1_size = max(40, width // 16)
    sub_size = max(24, width // 28)
    cta_size = max(18, width // 38)
    brand_size = max(16, width // 48)

    cta_text = cta_ar or cta_en

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{width}px;height:{height}px;overflow:hidden}}
body{{
  background:{brand_primary};
  display:flex;
  flex-direction:column;
  align-items:flex-end;
  justify-content:flex-end;
  padding:{pad}px;
  font-family:'Thmanyah','Segoe UI',Tahoma,sans-serif;
  position:relative;
}}
.top-bar{{
  position:absolute;top:0;left:0;right:0;
  height:4px;background:{brand_accent};
}}
.brand{{
  position:absolute;top:{max(18,pad//2)}px;left:{pad}px;
  color:{brand_accent};
  font-size:{brand_size}px;
  font-weight:700;
  letter-spacing:0.05em;
}}
.overlay{{
  position:absolute;inset:0;
  background:linear-gradient(to bottom, transparent 30%, rgba(0,0,0,0.75) 100%);
  pointer-events:none;
}}
.content{{
  position:relative;z-index:2;
  display:flex;flex-direction:column;align-items:flex-end;
  max-width:{int(width*0.88)}px;
}}
h1{{
  color:#F8F6F1;
  font-size:{h1_size}px;
  font-weight:900;
  text-align:right;
  line-height:1.25;
  margin-bottom:{max(12,pad//4)}px;
  direction:rtl;
}}
.subhead{{
  color:{brand_accent};
  font-size:{sub_size}px;
  font-weight:700;
  text-align:right;
  margin-bottom:{max(20,pad//3)}px;
  direction:rtl;
}}
.cta{{
  background:{brand_accent};
  color:#fff;
  font-size:{cta_size}px;
  font-weight:700;
  padding:{max(10,cta_size//2)}px {max(28,cta_size*1.5)}px;
  border-radius:999px;
  direction:rtl;
}}
.bottom-bar{{
  position:absolute;bottom:0;left:0;right:0;
  height:6px;background:{brand_accent};
}}
</style>
</head>
<body>
  <div class="top-bar"></div>
  <div class="brand">{project_name}</div>
  <div class="overlay"></div>
  <div class="content">
    <h1>{headline_ar}</h1>
    {f'<p class="subhead">{subhead_ar}</p>' if subhead_ar else ''}
    {f'<div class="cta">{cta_text}</div>' if cta_text else ''}
  </div>
  <div class="bottom-bar"></div>
</body>
</html>"""


async def _screenshot_url(url: str, width: int, height: int) -> bytes | None:
    """Screenshot URL using Playwright. Returns PNG bytes or None."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.goto(url, wait_until="networkidle", timeout=15000)
            png = await page.screenshot(clip={"x": 0, "y": 0, "width": width, "height": height})
            await browser.close()
            return png
    except ImportError:
        logger.debug("Playwright not installed — using Pillow fallback thumbnail")
        return None
    except Exception as exc:
        logger.warning("Playwright screenshot failed: %s", exc)
        return None


async def _pillow_thumbnail(html_bytes: bytes, width: int, height: int) -> bytes:
    """Fallback thumbnail using Pillow — renders a branded placeholder."""
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path

    def _draw():
        img = Image.new("RGB", (width, height), color=(0, 26, 77))
        draw = ImageDraw.Draw(img)
        # Simple placeholder: brand bar + "Open Design" label
        draw.rectangle([(0, 0), (width, 5)], fill=(65, 105, 225))
        draw.rectangle([(0, height - 5), (width, height)], fill=(65, 105, 225))
        try:
            font_path = Path(__file__).parent.parent.parent / "assets/fonts/thmanyah typeface/thmanyahsans/otf/thmanyahsans-Bold.otf"
            font = ImageFont.truetype(str(font_path), max(24, width // 30))
        except Exception:
            font = ImageFont.load_default(size=max(24, width // 30))
        label = "Open Design"
        bb = draw.textbbox((0, 0), label, font=font)
        lw, lh = bb[2] - bb[0], bb[3] - bb[1]
        draw.text(((width - lw) // 2, (height - lh) // 2), label, font=font, fill=(65, 105, 225))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    return await asyncio.to_thread(_draw)


async def generate_open_design_variant(
    asset_id: str,
    headline_ar: str,
    subhead_ar: str,
    cta_ar: str,
    cta_en: str,
    brand_primary: str,
    brand_accent: str,
    channel: str,
    width: int,
    height: int,
    upload_fn,  # async fn(bytes, filename, content_type) -> str  (R2 upload)
    project_name: str = "Therapia",
) -> dict:
    """
    Generate Variant C via Open Design daemon.
    Returns variant dict compatible with existing asset.variants schema.
    """
    settings = get_settings()

    if not settings.OPEN_DESIGN_ENABLED:
        return {
            "variant": "C",
            "label": "Open Design",
            "status": "skipped",
            "reason": "OPEN_DESIGN_ENABLED=false",
            "source": "open-design",
        }

    daemon = settings.OPEN_DESIGN_DAEMON_URL.rstrip("/")

    # 1. Health check — fail fast if daemon not running
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            health = await client.get(f"{daemon}/api/health")
            if not health.json().get("ok"):
                raise RuntimeError("daemon not healthy")
    except Exception as exc:
        logger.warning("Open Design daemon unavailable: %s", exc)
        return {
            "variant": "C", "label": "Open Design",
            "status": "failed", "error": f"Daemon unavailable: {exc}",
            "source": "open-design",
        }

    # 2. Build HTML card from brand tokens
    html = _build_html(
        headline_ar=headline_ar,
        subhead_ar=subhead_ar,
        cta_ar=cta_ar,
        cta_en=cta_en,
        brand_primary=brand_primary,
        brand_accent=brand_accent,
        width=width,
        height=height,
        project_name=project_name,
    )

    # 3. Save artifact via daemon
    identifier = hashlib.sha256(f"{asset_id}-open-design-C".encode()).hexdigest()[:16]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            save_resp = await client.post(
                f"{daemon}/api/artifacts/save",
                json={"identifier": identifier, "title": f"{project_name} Social Card", "html": html},
            )
            save_resp.raise_for_status()
            saved = save_resp.json()
    except Exception as exc:
        logger.error("Open Design save failed: %s", exc)
        return {
            "variant": "C", "label": "Open Design",
            "status": "failed", "error": str(exc),
            "source": "open-design",
        }

    artifact_url = f"{daemon}{saved['url']}"
    logger.info("Open Design artifact: %s", artifact_url)

    # 4. Screenshot → thumbnail
    png_bytes = await _screenshot_url(artifact_url, width, height)
    if not png_bytes:
        # Fallback: render thumbnail with Pillow
        png_bytes = await _pillow_thumbnail(html.encode(), min(400, width), min(400, height))

    # 5. Upload to R2
    try:
        vid = f"{asset_id}_vC"
        design_url = await upload_fn(html.encode(), f"{vid}.html", "text/html")
        thumb_url = await upload_fn(png_bytes, f"{vid}_thumb.jpg", "image/jpeg")
    except Exception as exc:
        logger.error("Open Design R2 upload failed: %s", exc)
        # Store artifact as data URL fallback
        import base64
        thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(png_bytes).decode()}"
        return {
            "variant": "C",
            "label": "Open Design",
            "description": "HTML artifact from Open Design daemon — RTL Arabic via browser shaping",
            "design_url": artifact_url,   # serve directly from daemon
            "thumbnail_url": thumb_b64,
            "source": "open-design",
            "artifact_path": saved.get("path"),
            "daemon_artifact_url": artifact_url,
            "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
            "status": "ok",
        }

    return {
        "variant": "C",
        "label": "Open Design",
        "description": "HTML artifact from Open Design daemon — RTL Arabic via browser shaping",
        "design_url": design_url,
        "thumbnail_url": thumb_url,
        "source": "open-design",
        "artifact_path": saved.get("path"),
        "daemon_artifact_url": artifact_url,
        "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
        "status": "ok",
    }
