"""
Design Agent — Two commercial app-marketing variants per asset:
  Variant A — product-in-use campaign (person using the app)
  Variant B — outcome/results campaign (person after using the app)
Both use commercial performance-marketing direction, not cinematic art.
"""
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import apply_text_overlay, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2

# ── Variant A: product-in-use app-marketing campaign ────────────────────────

ART_DIRECTOR_PROMPT = """You are a senior commercial art director for Saudi/Gulf app-marketing campaigns.
You produce fal.ai prompts that generate world-class commercial app-marketing assets.

DIRECTION — commercial growth campaign, NOT cinematic art:
- Saudi/Gulf professional actively using a phone or health app in real context
- Clean performance-marketing layout: strong person + clear context + copy zone
- Looks like a serious health-tech product launch campaign (think: Headspace, MyFitnessPal)
- No abstract metaphors, no AI movie stills, no decorative wellness posters
- Modern Saudi context: clean apartment, office, or urban lifestyle

REQUIRED:
- Real person with phone/app visible
- Clear bottom 35% gradient zone for Arabic text overlay
- Brand accent color as atmosphere, not decoration
- Benefit visible in the scene (person engaged, measurable action)

OUTPUT: fal.ai image prompt only. Max 120 words. No explanation. No quotes."""

# ── Variant B: commercial marketing campaign director ──────────────────────

COMMERCIAL_DIRECTOR_PROMPT = """You are a senior performance marketing creative director for Saudi/Gulf digital products.
You create fal.ai prompts for app-install and conversion campaigns.

DIRECTION — outcome/results campaign, distinct from Variant A which shows product-in-use:
- Show a Saudi/Gulf person AFTER using the product: confident, healthier, more successful
- Feature the transformation or result — not the app UI, the human outcome
- Professional advertising photography: intentional lighting, clean environment, premium quality
- Think: Nike Training Club campaign, Headspace results ad, health app success story — Gulf version
- High-contrast composition: hero person + clean background + aspirational energy

REQUIRED:
- Different composition from Variant A (A = using app, B = result of using app)
- Saudi Gulf person in aspirational but realistic setting
- Bottom 35% clear and dark for Arabic copy overlay
- No app screens, no phones — focus on the human transformation

OUTPUT: fal.ai prompt only. Max 120 words. No explanation."""

PLATFORM_DIMENSIONS = {
    "instagram_post":    (1080, 1080),
    "instagram_portrait":(1080, 1350),
    "instagram_story":   (1080, 1920),
    "linkedin_post":     (1200, 627),
    "x_post":            (1600, 900),
    "google_display":    (1200, 628),
}

PLATFORM_DIMS_FAL = {
    "instagram_post":    {"width": 1080, "height": 1080},
    "instagram_portrait":{"width": 1080, "height": 1350},
    "instagram_story":   {"width": 1080, "height": 1920},
    "linkedin_post":     {"width": 1200, "height": 627},
    "x_post":            {"width": 1600, "height": 900},
    "google_display":    {"width": 1200, "height": 628},
}

# Open CoDesign commercial principles applied to Variant B
OPENCODESIGN_PRINCIPLES = [
    "craft-polish.md — dramatic lighting, saturated brand colors, high production value",
    "frontend-design-anti-slop.md — no generic stock photo, no weak composition",
    "artifact-composition.md — benefit-focused composition, emotional outcome visible",
    "responsive-layout.md — design survives all platform exports cleanly",
    "Brand refs: Nike, Apple, Starbucks KSA — aspirational, conversion-grade campaign",
]


class DesignAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=ART_DIRECTOR_PROMPT, tools=[], max_tokens=200)
        self._commercial_agent = BaseAgent(
            system_prompt=COMMERCIAL_DIRECTOR_PROMPT, tools=[], max_tokens=200
        )

    async def _get_prompt(
        self, agent: BaseAgent, copy_en: str, copy_ar: str, channel: str,
        brand_colors: dict, brand_style: str, image_style: str, funnel_stage: str,
        brand_brief: str = "", dos: list | None = None, variant: str = "A",
    ) -> str:
        primary    = brand_colors.get("primary",    "#0A0A0A")
        accent     = brand_colors.get("accent",     "#C9A84C")
        secondary  = brand_colors.get("secondary",  "")
        background = brand_colors.get("background", primary)
        dos_text   = "; ".join((dos or [])[:3])

        if variant == "A":
            msg = (
                f"Platform: {channel} | Funnel: {funnel_stage}\n"
                f"BRAND COLORS: primary={background}, accent={accent}, secondary={secondary or 'none'}\n"
                f"VISUAL STYLE: {brand_style}\nIMAGE STYLE: {image_style}\n"
            )
        else:
            # Variant B: commercial campaign — bold advertising energy, benefit-focused
            msg = (
                f"Platform: {channel} | Funnel: {funnel_stage}\n"
                f"BRAND COLORS: primary={background}, accent={accent}\n"
                f"BRAND STYLE: {brand_style}\n"
                "DIRECTION: Bold commercial campaign visual. Show the benefit or outcome visually. "
                "High production value, dramatic composition, conversion-grade advertising energy.\n"
            )

        if brand_brief:
            msg += f"BRAND BRIEF: {brand_brief[:300]}\n"
        if dos_text:
            msg += f"BRAND DOS: {dos_text}\n"
        msg += (
            f"ARABIC COPY: {copy_ar[:100]}\nENGLISH COPY: {copy_en[:120]}\n\n"
            "Generate the fal.ai prompt now."
        )
        try:
            prompt = await agent.run(msg, None)  # type: ignore
            return prompt.strip().strip('"').strip("'")
        except Exception:
            if variant == "A":
                return (
                    f"Commercial app-marketing campaign, {brand_style} Saudi context, {image_style}, "
                    f"accent {accent} as rim light, background {background}, "
                    f"depth of field, clear bottom 35% for text, premium quality"
                )
            else:
                return (
                    f"Bold commercial advertising campaign, Saudi market, high production value, "
                    f"brand colors {background} and {accent}, dramatic lighting, confident person "
                    f"achieving a goal or using the product, aspirational Gulf lifestyle, "
                    f"conversion-grade composition, clear bottom 35% for text, premium ad quality, no text in image"
                )

    def _build_memory_snapshot(
        self, brand_mem, project_mem, channel: str, funnel_stage: str
    ) -> dict:
        """Record which memory fields were populated — shown in approval as proof."""
        snap: dict = {}
        if brand_mem:
            snap["brand_voice"]   = bool(brand_mem.brand_voice)
            snap["colors"]        = bool(brand_mem.color_palette)
            snap["visual_style"]  = bool(brand_mem.visual_style)
            snap["dos"]           = len(brand_mem.dos or [])
            snap["donts"]         = len(brand_mem.donts or [])
            snap["is_provisional"]= brand_mem.is_provisional
        if project_mem:
            snap["brand_brief"]        = bool(getattr(project_mem, "brand_brief", None))
            snap["icp"]                = bool(project_mem.icp)
            snap["positioning"]        = bool(project_mem.positioning)
            snap["tone"]               = bool(project_mem.tone)
            snap["funnel_goals"]       = bool(project_mem.funnel_goals)
            snap["approved_examples"]  = len(project_mem.approved_examples or [])
            snap["rejected_examples"]  = len(project_mem.rejected_examples or [])
            snap["excluded_topics"]    = len(
                (project_mem.constraints or {}).get("excluded_topics", [])
            )
        snap["channel"]       = channel
        snap["funnel_stage"]  = funnel_stage
        return snap

    async def generate_design(
        self, db: AsyncSession, project_id: str, asset_id: str,
        channel: str, copy_ar: str, copy_en: str,
        cta_ar: str = "", cta_en: str = "", num_variants: int = 1
    ) -> dict:
        try:
            brand_mem   = await get_brand_memory(db, project_id)
            project_mem = await get_project_memory(db, project_id)

            colors    = (brand_mem.color_palette or {}) if brand_mem else {}
            style     = (brand_mem.visual_style  or "modern professional") if brand_mem else "modern professional"
            img_style = (brand_mem.image_style   or "commercial app-marketing photography") if brand_mem else "commercial app-marketing"
            dos       = (brand_mem.dos or []) if brand_mem else []
            accent    = colors.get("accent", colors.get("primary", "#4169E1"))
            primary_color = colors.get("primary", colors.get("background", "#001A4D"))

            brief = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            fal_dims = PLATFORM_DIMS_FAL.get(platform_key, {"width": 1080, "height": 1080})

            text_ar = f"{copy_ar}\n{cta_ar}".strip() if copy_ar or cta_ar else ""
            text_en = f"{copy_en}\n{cta_en}".strip() if copy_en or cta_en else ""

            memory_snapshot = self._build_memory_snapshot(brand_mem, project_mem, channel, "awareness")

            # ── Generate prompts sequentially (avoid asyncio CancelledError) ──
            prompt_a = await self._get_prompt(
                self, copy_en, copy_ar, channel, colors, style, img_style,
                "awareness", brief, dos, variant="A"
            )
            prompt_b = await self._get_prompt(
                self._commercial_agent, copy_en, copy_ar, channel, colors, style, img_style,
                "awareness", brief, dos, variant="B"
            )

            async def _generate_one(prompt: str, variant_label: str, vid_suffix: str) -> dict:
                try:
                    img_bytes = await generate_image_fal(
                        prompt, "fal-ai/flux/schnell", fal_dims["width"], fal_dims["height"]
                    )
                    with_text = await apply_text_overlay(
                        img_bytes, text_ar, text_en,
                        brand_primary=primary_color, brand_accent=accent,
                    )
                    thumb = await create_thumbnail(with_text)
                    vid   = f"{asset_id}_{vid_suffix}"
                    durl  = await upload_to_r2(with_text, f"{vid}.png",       "image/png")
                    turl  = await upload_to_r2(thumb,     f"{vid}_thumb.jpg", "image/jpeg")
                    return {
                        "variant":       variant_label,
                        "design_url":    durl,
                        "thumbnail_url": turl,
                        "fal_prompt":    prompt[:200],
                        "status":        "ok",
                    }
                except BaseException as exc:  # catch CancelledError (Python 3.13 BaseException)
                    return {"variant": variant_label, "error": str(exc), "status": "failed"}

            # Run sequentially — avoids CancelledError propagation in asyncio.gather
            variant_a_data = await _generate_one(prompt_a, "A", "vA")
            variant_b_data = await _generate_one(prompt_b, "B", "vB")

            # Variant A is primary; fallback to B if A failed
            primary_variant = variant_a_data if variant_a_data["status"] == "ok" else variant_b_data
            first_url   = primary_variant.get("design_url")
            first_thumb = primary_variant.get("thumbnail_url")

            variants = [
                {
                    **variant_a_data,
                    "label":       "Campaign Variant A",
                    "description": "Product-in-use: Saudi professional using the app, benefit visible, app context clear",
                    "source":      "fal-ai/flux/schnell + DeepSeek commercial art director",
                },
                {
                    **variant_b_data,
                    "label":       "Campaign Variant B",
                    "description": "Result-focused: Saudi person after using Therapia, transformation visible, outcome clear",
                    "source":      "fal-ai/flux/schnell + DeepSeek commercial director",
                    "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                },
            ]

            return {
                "design_url":      first_url,
                "thumbnail_url":   first_thumb,
                "variants":        variants,
                "memory_snapshot": memory_snapshot,
                "model_used":      "fal-ai/flux/schnell + DeepSeek (A: product-in-use, B: outcome campaign)",
                "notes":           ["provisional" if (brand_mem and brand_mem.is_provisional) else "approved-brand"],
            }
        except Exception as exc:
            return {"error": str(exc), "design_url": None, "thumbnail_url": None, "variants": [], "memory_snapshot": {}}
