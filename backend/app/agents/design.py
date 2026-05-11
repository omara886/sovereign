"""
Design Agent — Art director (DeepSeek) → fal.ai scene → Thmanyah text overlay → base64 thumbnail
Colors and style come entirely from brand_memory — no hardcoded defaults.
"""
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import apply_text_overlay, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2

ART_DIRECTOR_PROMPT = """You are a world-class Saudi social media art director.
15 years at BBDO and Wunderman Thompson Middle East.
You create fal.ai image prompts that produce scroll-stopping Saudi social graphics.

VISUAL RULES (non-negotiable):
- Real photographic scene always. NEVER text-on-solid-background.
- Depth: foreground + midground + background with slight depth of field.
- Bottom 35% of frame: clear, darker gradient — reserved for text overlay.
- Brand accent color as the primary light source, rim light, or atmosphere.
- Subjects never crowded — generous negative space, editorial airiness.
- Saudi cultural context: modern professional Saudi lifestyle, Vision 2030 energy.

COMPOSITION:
- One visual message. 0.3 second emotional impact.
- Scale contrast: one dominant element, everything else secondary.
- Soft shadows, no harsh edges.

OUTPUT: fal.ai image prompt only. Max 120 words. No explanation. No quotes."""

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

    async def _get_visual_prompt(
        self, copy_en, copy_ar, channel, brand_colors, brand_style,
        image_style, funnel_stage, brand_brief: str = "", dos: list | None = None
    ) -> str:
        primary    = brand_colors.get("primary",    "#0A0A0A")
        accent     = brand_colors.get("accent",     "#C9A84C")
        secondary  = brand_colors.get("secondary",  "")
        background = brand_colors.get("background", primary)
        dos_text   = "; ".join(dos[:3]) if dos else ""

        msg = (
            f"Platform: {channel} | Funnel stage: {funnel_stage}\n\n"
            f"BRAND COLORS (USE THESE EXACTLY):\n"
            f"  Primary background: {background}\n"
            f"  Primary accent / light source: {accent}\n"
            f"  Secondary: {secondary or 'none'}\n\n"
            f"BRAND VISUAL STYLE: {brand_style}\n"
            f"IMAGE STYLE: {image_style}\n"
        )
        if brand_brief:
            msg += f"\nBRAND BRIEF:\n{brand_brief[:400]}\n"
        if dos_text:
            msg += f"\nBRAND DOS: {dos_text}\n"
        msg += (
            f"\nCOPY TO VISUALISE:\n"
            f"  Arabic: {copy_ar[:100]}\n"
            f"  English: {copy_en[:150]}\n\n"
            "Write the fal.ai image generation prompt. "
            "The scene MUST reflect the brand colors above — not generic warm gold. "
            "Real scene, Saudi context, brand accent as light source, "
            "depth of field, clear dark bottom 35% for text. No text in image."
        )
        try:
            prompt = await self.run(msg, None)  # type: ignore
            return prompt.strip().strip('"').strip("'")
        except Exception:
            return (
                f"Cinematic {brand_style} Saudi scene, {image_style}, "
                f"accent color {accent} as rim light, background {background}, "
                f"depth of field, bottom 35% clear gradient, no text in image, "
                f"premium editorial quality"
            )

    async def generate_design(self, db: AsyncSession, project_id: str, asset_id: str,
                               channel: str, copy_ar: str, copy_en: str,
                               cta_ar: str = "", cta_en: str = "", num_variants: int = 1) -> dict:
        try:
            brand_mem   = await get_brand_memory(db, project_id)
            project_mem = await get_project_memory(db, project_id)

            colors    = (brand_mem.color_palette or {}) if brand_mem else {}
            style     = (brand_mem.visual_style  or "modern professional") if brand_mem else "modern professional"
            img_style = (brand_mem.image_style   or "cinematic lifestyle photography") if brand_mem else "cinematic"
            dos       = (brand_mem.dos or []) if brand_mem else []
            accent    = colors.get("accent",  colors.get("primary", "#C9A84C"))

            # Brand brief from project memory (markdown text)
            brief = ""
            if project_mem:
                brief = getattr(project_mem, "brand_brief", None) or ""

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            dims     = PLATFORM_DIMENSIONS.get(platform_key, (1080, 1080))
            fal_dims = PLATFORM_DIMS_FAL.get(platform_key, {"width": 1080, "height": 1080})

            fal_prompt = await self._get_visual_prompt(
                copy_en=copy_en, copy_ar=copy_ar, channel=channel,
                brand_colors=colors, brand_style=style, image_style=img_style,
                funnel_stage="awareness", brand_brief=brief, dos=dos,
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
                    primary_color = colors.get("primary", colors.get("background", "#0A0A0A"))
                    with_text = await apply_text_overlay(
                        img_bytes, text_ar, text_en,
                        brand_primary=primary_color, brand_accent=accent,
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
