"""
Design Agent — Template-driven commercial marketing renderer.

Architecture:
  1. DeepSeek writes a SHORT fal.ai prompt for BACKGROUND ONLY (no text, no people preferred)
  2. fal.ai generates background atmosphere/scene
  3. Pillow templates compose the final design:
     - Variant A: Product Showcase (brand frame, Arabic headline, CTA)
     - Variant B: Infographic Outcome (metric hero, benefit blocks, Arabic headline)

Arabic text is NEVER baked into fal.ai prompts.
Arabic is rendered by the app with Thmanyah font + bidi + controlled line lengths.
"""
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import render_product_showcase, render_infographic, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2

# ── Permanent negative prompt block (Rule 3 from research) ──────────────────
# Anti-realism + anti-text-takeover applied to EVERY generation

NEGATIVE_PROMPT = (
    "photorealistic man, businessman in suit, shemagh portrait, stock photo, "
    "plastic skin, HDR face, shallow depth of field, cinematic portrait, "
    "neon blue purple gradient, glowing particles, generic corporate photography, "
    "giant text, random glyphs, broken letters, arabic letters in image, "
    "latin letters, numbers in image, watermark, signature, "
    "cluttered layout, cheap ad template, social media ad template, "
    "oversized text, huge letters, dominant typography, text covering face, "
    "wall of text, centered giant title, multiple random letters, "
    "broken glyphs, latin-looking fake arabic, caption overlay, logo soup, "
    "too many decorative elements, visual clutter, random icons, "
    "busy background, unbalanced hierarchy, textured noise everywhere, "
    "dribbble-style glow, floating particles, generic futuristic interface, "
    "blue purple gradient, neon tech background, AI face symmetry"
)

# ── Variant A: product showcase background (format-first prompting) ──────────

BACKGROUND_A_PROMPT = """You are a commercial background art director.
Generate a fal.ai prompt for a BACKGROUND IMAGE ONLY — no text anywhere.

PROMPT ORDER (Rule 4): format → style → layout → subject → palette → exclusions

BACKGROUND DIRECTION (Variant A — product showcase composition):
- Format: premium brand campaign poster background
- Visual language: flat 3D illustration hybrid OR editorial product photography
- Composition: hero object left or center, generous negative space bottom 40% for text overlay
- Subject: phone/health device OR abstract health-tech visual element, NO people preferred
- Palette: brand primary dark color dominant, accent as highlight
- Mood: premium, restrained, contemporary Saudi health-tech brand

Text-safe zone: bottom 45% must be clean dark gradient — Arabic headline goes here.

OUTPUT: fal.ai prompt for background only. Max 90 words. No explanation."""

# ── Variant B: infographic background (format-first prompting) ───────────────

BACKGROUND_B_PROMPT = """You are a commercial background art director.
Generate a fal.ai prompt for a BACKGROUND IMAGE ONLY — no text anywhere.

PROMPT ORDER (Rule 4): format → style → layout → subject → palette → exclusions

BACKGROUND DIRECTION (Variant B — infographic/data visual):
- Format: information design poster background, modular editorial grid aesthetic
- Visual language: geometric vector shapes, abstract data visualization, icon-led composition
- Composition: structured grid pattern OR abstract circles/arcs suggesting health metrics
- Subject: abstract geometric forms, no people, no faces, no devices
- Palette: brand primary color dominant, soft gradient overlay
- Mood: premium digital health, restrained, systematic, contemporary

The overlay will add a large metric number + Arabic text over this background.

OUTPUT: fal.ai prompt only. Max 90 words. No explanation."""

PLATFORM_DIMS_FAL = {
    "instagram_post":    {"width": 1080, "height": 1080},
    "instagram_portrait":{"width": 1080, "height": 1350},
    "instagram_story":   {"width": 1080, "height": 1920},
    "linkedin_post":     {"width": 1200, "height": 627},
    "x_post":            {"width": 1600, "height": 900},
    "google_display":    {"width": 1200, "height": 628},
}

# Open CoDesign principles used in the template renderer
OPENCODESIGN_PRINCIPLES = [
    "artifact-composition.md — structured brand template, not raw prompt output",
    "craft-polish.md — controlled spacing, contrast, hierarchy",
    "frontend-design-anti-slop.md — no generic AI posters, no baked Arabic text",
    "editorial-typography.jsx — Thmanyah Arabic, RTL, bidi, max 2 headline lines",
    "accessibility-states.md — contrast validated, safe zones enforced",
]


class DesignAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=BACKGROUND_A_PROMPT, tools=[], max_tokens=150)
        self._bg_b_agent = BaseAgent(
            system_prompt=BACKGROUND_B_PROMPT, tools=[], max_tokens=150
        )

    async def _get_bg_prompt(self, agent: BaseAgent, copy_en: str, brand_colors: dict,
                              brand_style: str, funnel_stage: str, brief: str) -> str:
        primary = brand_colors.get("primary", "#001A4D")
        accent  = brand_colors.get("accent",  "#4169E1")
        # Format-first prompt structure (Rule 4 from research)
        msg = (
            f"BRAND: {brand_style}\n"
            f"PALETTE: primary {primary}, accent {accent}\n"
            f"CAMPAIGN: {copy_en[:80]}\n"
        )
        if brief:
            msg += f"BRAND BRIEF: {brief[:150]}\n"
        msg += (
            "\nGenerate the fal.ai background prompt using format-first structure:\n"
            "[format] → [visual language] → [composition] → [subject] → [palette] → [exclusions]\n"
            "Reserve bottom 45% as clear text-safe zone. No text in image."
        )
        try:
            p = await agent.run(msg, None)  # type: ignore
            return p.strip().strip('"').strip("'")
        except Exception:
            return (
                f"Premium campaign poster background, flat 3D illustration hybrid, "
                f"asymmetrical modular grid, hero element center-left, "
                f"generous negative space bottom 45% for text overlay, "
                f"brand color {primary} dominant, accent {accent} highlights, "
                f"matte vector and soft gradient, high-end health-tech brand aesthetic, "
                f"no text, no people, no watermark, no stock photo look"
            )

    def _build_memory_snapshot(self, brand_mem, project_mem, channel: str) -> dict:
        snap: dict = {"channel": channel, "template_engine": "Pillow deterministic"}
        if brand_mem:
            snap["brand_voice"]    = bool(brand_mem.brand_voice)
            snap["colors"]         = bool(brand_mem.color_palette)
            snap["visual_style"]   = bool(brand_mem.visual_style)
            snap["dos"]            = len(brand_mem.dos or [])
            snap["donts"]          = len(brand_mem.donts or [])
            snap["is_provisional"] = brand_mem.is_provisional
        if project_mem:
            snap["brand_brief"]       = bool(getattr(project_mem, "brand_brief", None))
            snap["icp"]               = bool(project_mem.icp)
            snap["positioning"]       = bool(project_mem.positioning)
            snap["tone"]              = bool(project_mem.tone)
            snap["funnel_goals"]      = bool(project_mem.funnel_goals)
            snap["approved_examples"] = len(project_mem.approved_examples or [])
            snap["rejected_examples"] = len(project_mem.rejected_examples or [])
            snap["excluded_topics"]   = len(
                (project_mem.constraints or {}).get("excluded_topics", [])
            )
        return snap

    def _extract_metric(self, copy_ar: str) -> tuple[str, str]:
        """Extract a key metric from the Arabic copy (e.g., '٨' + 'دقائق')."""
        import re
        # Look for Arabic numerals or Eastern Arabic numerals
        patterns = [
            (r'(\d+)\s*(دقيقة|دقائق|ثانية|ساعة)', lambda m: (m.group(1), m.group(2))),
            (r'([٠-٩]+)\s*(دقيقة|دقائق)', lambda m: (m.group(1), m.group(2))),
            (r'(\d+)\s*(خطوة|خطوات|يوم|أيام|أسبوع)', lambda m: (m.group(1), m.group(2))),
        ]
        for pattern, extractor in patterns:
            m = re.search(pattern, copy_ar)
            if m:
                try:
                    val, label = extractor(m)
                    return val, label
                except Exception:
                    pass
        return "٨", "دقائق"  # default Therapia key metric

    def _extract_benefits(self, copy_ar: str, copy_en: str) -> list[str]:
        """Extract 3 short benefit phrases for the infographic blocks."""
        # Try to split copy into short phrases
        import re
        phrases = re.split(r'[.،\n]', copy_ar)
        clean = [p.strip() for p in phrases if len(p.strip()) > 3 and len(p.strip()) < 25]
        if len(clean) >= 3:
            return clean[:3]
        # Fallback: generic Therapia benefits
        return ["تقييم صحي شامل", "٨ دقائق فقط", "خطة شخصية"]

    async def generate_design(
        self, db: AsyncSession, project_id: str, asset_id: str,
        channel: str, copy_ar: str, copy_en: str,
        cta_ar: str = "", cta_en: str = "", num_variants: int = 1
    ) -> dict:
        try:
            brand_mem   = await get_brand_memory(db, project_id)
            project_mem = await get_project_memory(db, project_id)

            colors    = (brand_mem.color_palette or {}) if brand_mem else {}
            style     = (brand_mem.visual_style or "commercial app-marketing") if brand_mem else "commercial app-marketing"
            primary   = colors.get("primary", colors.get("background", "#001A4D"))
            accent    = colors.get("accent",  colors.get("secondary",  "#4169E1"))
            brief     = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            fal_dims = PLATFORM_DIMS_FAL.get(platform_key, {"width": 1080, "height": 1080})
            w, h = fal_dims["width"], fal_dims["height"]

            memory_snapshot = self._build_memory_snapshot(brand_mem, project_mem, channel)

            # ── Background prompts (no Arabic text) ──
            bg_prompt_a = await self._get_bg_prompt(
                self, copy_en, colors, style, "awareness", brief
            )
            bg_prompt_b = await self._get_bg_prompt(
                self._bg_b_agent, copy_en, colors, style, "awareness", brief
            )

            # ── Extract infographic data from copy ──
            metric_val, metric_lbl = self._extract_metric(copy_ar)
            benefits = self._extract_benefits(copy_ar, copy_en)

            # Use flux/schnell (fast, 4 steps) — no negative_prompt support
            # Switch to "fal-ai/flux-pro" or "fal-ai/flux/dev" for negative prompts
            FAL_MODEL = "fal-ai/flux/schnell"

            async def _make_variant_a() -> dict:
                try:
                    bg = await generate_image_fal(
                        bg_prompt_a,
                        FAL_MODEL, w, h,
                        negative_prompt=NEGATIVE_PROMPT,
                    )
                    final_img = await render_product_showcase(
                        w, h,
                        headline_ar=" ".join(copy_ar.split()[:6]),  # max 6 words for readable Arabic headline
                        subhead_ar=cta_ar[:40] if cta_ar else "",
                        cta_ar=cta_ar[:25] if cta_ar else "",
                        cta_en=cta_en[:25] if cta_en else "",
                        brand_primary=primary,
                        brand_accent=accent,
                        bg_bytes=bg,
                    )
                    thumb = await create_thumbnail(final_img)
                    vid   = f"{asset_id}_vA"
                    durl  = await upload_to_r2(final_img, f"{vid}.jpg", "image/jpeg")
                    turl  = await upload_to_r2(thumb,     f"{vid}_thumb.jpg", "image/jpeg")
                    return {
                        "variant": "A", "label": "Product Showcase",
                        "description": "Brand-controlled template: Arabic headline + CTA + product frame. Thmanyah font, RTL layout, brand colors.",
                        "design_url": durl, "thumbnail_url": turl,
                        "bg_prompt": bg_prompt_a, "status": "ok",
                        "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                    }
                except BaseException as exc:
                    return {"variant": "A", "label": "Product Showcase",
                            "error": str(exc), "status": "failed"}

            async def _make_variant_b() -> dict:
                try:
                    bg = await generate_image_fal(
                        bg_prompt_b,
                        FAL_MODEL, w, h,
                        negative_prompt=NEGATIVE_PROMPT,
                    )
                    final_img = await render_infographic(
                        w, h,
                        headline_ar=" ".join(copy_ar.split()[:6]),  # max 6 words for readable Arabic headline
                        benefits=benefits,
                        metric_value=metric_val,
                        metric_label=metric_lbl,
                        cta_ar=cta_ar[:25] if cta_ar else "",
                        cta_en=cta_en[:25] if cta_en else "",
                        brand_primary=primary,
                        brand_accent=accent,
                        bg_bytes=bg,
                    )
                    thumb = await create_thumbnail(final_img)
                    vid   = f"{asset_id}_vB"
                    durl  = await upload_to_r2(final_img, f"{vid}.jpg", "image/jpeg")
                    turl  = await upload_to_r2(thumb,     f"{vid}_thumb.jpg", "image/jpeg")
                    return {
                        "variant": "B", "label": "Infographic Outcome",
                        "description": "Brand-controlled template: metric hero + benefit blocks + Arabic headline. No text baked in fal.ai.",
                        "design_url": durl, "thumbnail_url": turl,
                        "bg_prompt": bg_prompt_b, "status": "ok",
                        "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                    }
                except BaseException as exc:
                    return {"variant": "B", "label": "Infographic Outcome",
                            "error": str(exc), "status": "failed"}

            variant_a = await _make_variant_a()
            variant_b = await _make_variant_b()

            primary_variant = variant_a if variant_a["status"] == "ok" else variant_b
            variants = [variant_a, variant_b]

            return {
                "design_url":      primary_variant.get("design_url"),
                "thumbnail_url":   primary_variant.get("thumbnail_url"),
                "variants":        variants,
                "memory_snapshot": memory_snapshot,
                "model_used":      "Template renderer (Pillow) + fal.ai background + Thmanyah font",
                "notes":           ["template-driven", "arabic-rtl-safe", "brand-controlled"],
            }
        except Exception as exc:
            return {
                "error": str(exc), "design_url": None, "thumbnail_url": None,
                "variants": [], "memory_snapshot": {}
            }
