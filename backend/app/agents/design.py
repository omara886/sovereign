"""
Design Agent — Two variants per asset:
  Variant A (FAL Option)         — cinematic Saudi lifestyle scene via fal.ai
  Variant B (Open CoDesign)      — editorial typographic design using open-codesign principles

Open CoDesign resources applied to Variant B:
  - editorial-typography.jsx  → Arabic/English typographic hierarchy
  - craft-polish.md           → spacing, contrast, edge treatment, rhythm
  - frontend-design-anti-slop.md → no generic gradients, no default-card syndrome
  - Brand refs: Linear, Notion, Stripe → clean, minimal, product-manager-grade
"""
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import apply_text_overlay, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2

# ── Variant A: cinematic lifestyle art director ─────────────────────────────

ART_DIRECTOR_PROMPT = """You are a world-class Saudi social media art director.
15 years at BBDO and Wunderman Thompson Middle East.
You create fal.ai image prompts for scroll-stopping Saudi social graphics.

VISUAL RULES:
- Real photographic scene always. NEVER text-on-solid-background.
- Depth: foreground + midground + background with slight depth of field.
- Bottom 35% of frame: clear, darker gradient — reserved for text overlay.
- Brand accent color as the primary light source, rim light, or atmosphere.
- Subjects never crowded — generous negative space, editorial airiness.
- Saudi cultural context: modern professional Saudi lifestyle, Vision 2030 energy.
- One visual message. 0.3 second emotional impact. Scale contrast.

OUTPUT: fal.ai image prompt only. Max 120 words. No explanation. No quotes."""

# ── Variant B: commercial marketing campaign director ──────────────────────

COMMERCIAL_DIRECTOR_PROMPT = """You are a senior commercial advertising director for Saudi brands.
Your work runs in malls, apps, Instagram ads, and LinkedIn campaigns.
You create bold, conversion-driven campaign visuals that make people stop and act.

COMMERCIAL MARKETING RULES:
- Bold advertising composition — hero product, service benefit, or emotional outcome
- Strong campaign energy: the image should feel like a SAR 50,000 ad shoot
- Dramatic lighting, saturated but premium brand colors, high production value
- Show the RESULT or BENEFIT visually — not the product itself, the transformation
- Saudi commercial aesthetic: aspirational, modern, prosperous, aspirational Gulf
- If health app: show confident healthy person, measurable goal achieved, doctor-trusted
- If B2B SaaS: show leader using the tool, team succeeding, measurable business win
- Strong visual tension: something is about to happen or just happened
- Bottom 35% dark gradient clear for text

OUTPUT: fal.ai image prompt for commercial campaign visual. Max 120 words. No explanation. No quotes."""

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
                    f"Cinematic {brand_style} Saudi scene, {image_style}, "
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
            img_style = (brand_mem.image_style   or "cinematic lifestyle photography") if brand_mem else "cinematic"
            dos       = (brand_mem.dos or []) if brand_mem else []
            accent    = colors.get("accent", colors.get("primary", "#4169E1"))
            primary_color = colors.get("primary", colors.get("background", "#001A4D"))

            brief = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            fal_dims = PLATFORM_DIMS_FAL.get(platform_key, {"width": 1080, "height": 1080})

            text_ar = f"{copy_ar}\n{cta_ar}".strip() if copy_ar or cta_ar else ""
            text_en = f"{copy_en}\n{cta_en}".strip() if copy_en or cta_en else ""

            memory_snapshot = self._build_memory_snapshot(brand_mem, project_mem, channel, "awareness")

            # ── Generate both variants concurrently ──────────────────────────
            prompt_a, prompt_b = await asyncio.gather(
                self._get_prompt(
                    self, copy_en, copy_ar, channel, colors, style, img_style,
                    "awareness", brief, dos, variant="A"
                ),
                self._get_prompt(
                    self._commercial_agent, copy_en, copy_ar, channel, colors, style, img_style,
                    "awareness", brief, dos, variant="B"
                ),
            )

            async def _generate_variant(prompt: str, variant_label: str, vid_suffix: str) -> dict:
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
                        "variant":    variant_label,
                        "design_url": durl,
                        "thumbnail_url": turl,
                        "fal_prompt": prompt,
                        "status": "ok",
                    }
                except Exception as exc:
                    return {"variant": variant_label, "error": str(exc), "status": "failed"}

            variant_a_data, variant_b_data = await asyncio.gather(
                _generate_variant(prompt_a, "A", "vA"),
                _generate_variant(prompt_b, "B", "vB"),
            )

            # Variant A is primary; fallback to B if A failed
            primary_variant = variant_a_data if variant_a_data["status"] == "ok" else variant_b_data
            first_url   = primary_variant.get("design_url")
            first_thumb = primary_variant.get("thumbnail_url")

            variants = [
                {
                    **variant_a_data,
                    "label":       "FAL Option",
                    "description": "Cinematic Saudi lifestyle scene — real photography, depth, cultural context",
                    "source":      "fal-ai/flux/schnell + DeepSeek cinematic art director",
                },
                {
                    **variant_b_data,
                    "label":       "Commercial Option",
                    "description": "Bold campaign visual — high-production advertising, benefit-focused, conversion-grade",
                    "source":      "fal-ai/flux/schnell + DeepSeek commercial director",
                    "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                },
            ]

            return {
                "design_url":      first_url,
                "thumbnail_url":   first_thumb,
                "variants":        variants,
                "memory_snapshot": memory_snapshot,
                "model_used":      "fal-ai/flux/schnell + DeepSeek (A: cinematic, B: open-codesign editorial)",
                "notes":           ["provisional" if (brand_mem and brand_mem.is_provisional) else "approved-brand"],
            }
        except Exception as exc:
            return {"error": str(exc), "design_url": None, "thumbnail_url": None, "variants": [], "memory_snapshot": {}}
