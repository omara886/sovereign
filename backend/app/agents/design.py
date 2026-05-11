"""
Design Agent — rebuilt per fal-ai-media + content-engine + frontend-design skills.
Art director (DeepSeek) → fal.ai scene → Thmanyah text overlay → base64 thumbnail
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import apply_text_overlay, create_thumbnail
from app.tools.memory_tools import get_brand_memory
from app.tools.r2_tools import upload_to_r2

_DESIGN_MD = ""
try:
    _p = Path(__file__).parent.parent.parent / "design-systems" / "therapia" / "DESIGN.md"
    if _p.exists():
        _DESIGN_MD = _p.read_text()[:800]
except Exception:
    pass

ART_DIRECTOR_PROMPT = f"""You are a world-class Saudi social media art director.
15 years at BBDO and Wunderman Thompson Middle East.
You create fal.ai image prompts that produce scroll-stopping premium Saudi social graphics.

OPEN-CODESIGN VISUAL DNA (same system as the UI — UI and content must feel like one team):

SPACING: 8pt grid. Generous breathing room. Padding like 24px safe zone around content.
Equivalent in image: subjects never crowded, generous negative space, editorial airiness.

COLOR TOKENS:
- Background: warm dark (not cold blue-black — think warm charcoal, oklch 0.18 warmth)
- Accent: gold (#C9A84C, oklch 0.74 0.13 75) — use as warm light source, rim light, or accent element
- Surface: slightly lighter than background — layers visible as distinct planes
- Text area (bottom 35%): darker overlay, smooth gradient, enough contrast for text

TYPOGRAPHY HIERARCHY (maps to image visual hierarchy):
- Display: large, dominant, serif energy — one headline element
- Body: smaller, secondary — breathing room from headline
- The same scale ratio as: display-2xl(48px) > body-lg(17px) ≈ 2.8x ratio

RADIUS / SOFTNESS:
- Radius-md = 10px, radius-xl = 14px → scenes should feel curved, not harsh
- Soft shadows, warm light, no hard edges in composition
- organic shapes, rounded corners in any prop/object visible

MOTION FEEL (static image that implies motion):
- Ease-out energy: things settling, not static. Slight depth of field = motion implied.

DESIGN SYSTEM:
{_DESIGN_MD}

SKILLS APPLIED (content-engine + fal-ai-media + frontend-design):

CONTENT-ENGINE:
- One visual, one message. 0.3 second emotional impact.
- Copy reinforces image; image does not repeat copy.

VISUAL COMPOSITION:
- ALWAYS a real scene. NEVER text-on-color background.
- Depth: foreground + midground + background.
- Gold as accent/light source. Bottom 35% clear, warm gradient, for text overlay.

SAUDI CULTURAL CONTEXT:
- Riyadh skyline at golden hour, modern Saudi professional, family warmth,
  desert-meets-modern aesthetic, Vision 2030 energy.
- Gold = premium and authentic in Saudi context.

FAL-AI-MEDIA skill:
- Instagram square: cinematic, warm, lifestyle — same warmth as the UI's warm dark tokens
- LinkedIn landscape: professional, editorial clean — same token hierarchy, more whitespace

HARD RULES:
- Real scene always. No text-on-background.
- Warm dark background always (not cold, not blue, not clinical white)
- Output ONLY the fal.ai prompt. Max 120 words. No explanation."""

PLATFORM_DIMENSIONS = {
    "instagram_post":   (1080, 1080),
    "instagram_story":  (1080, 1920),
    "linkedin_post":    (1200, 627),
    "x_post":           (1600, 900),
    "google_display":   (1200, 628),
}

PLATFORM_DIMS_FAL = {
    "instagram_post":   {"width": 1080, "height": 1080},
    "instagram_story":  {"width": 1080, "height": 1920},
    "linkedin_post":    {"width": 1200, "height": 627},
    "x_post":           {"width": 1600, "height": 900},
    "google_display":   {"width": 1200, "height": 628},
}


class DesignAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=ART_DIRECTOR_PROMPT, tools=[], max_tokens=200)

    async def _get_visual_prompt(self, copy_en, copy_ar, channel, brand_colors, brand_style, image_style, funnel_stage) -> str:
        primary = brand_colors.get("primary", "#0A0A0A")
        accent  = brand_colors.get("accent",  "#C9A84C")
        msg = (
            f"Platform: {channel}\nFunnel stage: {funnel_stage}\n"
            f"Brand style: {brand_style}\nImage style: {image_style}\n"
            f"Brand colors: primary={primary}, accent={accent}\n"
            f"English copy: {copy_en[:200]}\nArabic copy: {copy_ar[:100]}\n\n"
            "Generate the fal.ai visual prompt. Real scene, Saudi context, "
            "brand accent color, depth, clear bottom 35% for text overlay."
        )
        try:
            prompt = await self.run(msg, None)  # type: ignore
            return prompt.strip().strip('"').strip("'")
        except Exception:
            return (
                f"Cinematic {brand_style} scene, Saudi modern lifestyle, "
                f"golden hour warm light, {image_style}, depth with foreground blur, "
                f"accent color {accent}, dark background {primary}, "
                f"premium editorial quality, bottom 35% clear, no text in image"
            )

    async def generate_design(self, db: AsyncSession, project_id: str, asset_id: str,
                               channel: str, copy_ar: str, copy_en: str,
                               cta_ar: str = "", cta_en: str = "", num_variants: int = 1) -> dict:
        try:
            brand_mem = await get_brand_memory(db, project_id)
            colors    = (brand_mem.color_palette or {}) if brand_mem else {}
            style     = (brand_mem.visual_style  or "dark luxury, warm editorial") if brand_mem else "dark luxury"
            img_style = (brand_mem.image_style   or "cinematic lifestyle photography") if brand_mem else "cinematic"
            primary   = colors.get("primary", "#0A0A0A")
            accent    = colors.get("accent",  "#C9A84C")

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            dims     = PLATFORM_DIMENSIONS.get(platform_key, (1080, 1080))
            fal_dims = PLATFORM_DIMS_FAL.get(platform_key, {"width": 1080, "height": 1080})

            fal_prompt = await self._get_visual_prompt(
                copy_en=copy_en, copy_ar=copy_ar, channel=channel,
                brand_colors=colors, brand_style=style, image_style=img_style,
                funnel_stage="awareness",
            )

            text_ar = f"{copy_ar}\n{cta_ar}".strip() if copy_ar or cta_ar else ""
            text_en = f"{copy_en}\n{cta_en}".strip() if copy_en or cta_en else ""

            variants    = []
            first_url   = None
            first_thumb = None

            for i in range(max(1, num_variants)):
                try:
                    img_bytes = await generate_image_fal(
                        fal_prompt, "fal-ai/flux/schnell",
                        fal_dims["width"], fal_dims["height"]
                    )
                    with_text = await apply_text_overlay(
                        img_bytes, text_ar, text_en,
                        brand_primary=primary, brand_accent=accent,
                    )
                    thumb = await create_thumbnail(with_text)

                    vid  = f"{asset_id}_v{i}"
                    durl = await upload_to_r2(with_text, f"{vid}.png",      "image/png")
                    turl = await upload_to_r2(thumb,     f"{vid}_thumb.jpg","image/jpeg")

                    variants.append({"variant": i + 1, "design_url": durl, "thumbnail_url": turl})
                    if i == 0:
                        first_url   = durl
                        first_thumb = turl
                except Exception as ve:
                    variants.append({"variant": i + 1, "error": str(ve)})

            return {
                "design_url":    first_url,
                "thumbnail_url": first_thumb,
                "variants":      variants,
                "fal_prompt":    fal_prompt,
                "model_used":    "fal-ai/flux/schnell + DeepSeek-art-director",
                "notes": ["provisional" if (brand_mem and brand_mem.is_provisional) else "approved-brand"],
            }
        except Exception as exc:
            return {"error": str(exc), "design_url": None, "thumbnail_url": None, "variants": []}
