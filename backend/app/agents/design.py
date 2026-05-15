"""
Design Agent — Stage 05: Constrained prompt compilation + Stage 06: Generation.

DeepSeek is now a PROMPT COMPILER, not a freestyle LLM:
  - Receives: strategy, concept, copy_blocks, visual_plan, + ALL skill rules
  - Generates 3 candidate prompts, self-scores each, selects best 1-2
  - Cannot skip constraints or ignore layout/text-safe-zone rules

Stages:
  05_prompt_generation  — DeepSeek compiles + self-scores 3 prompts
  06_image_generation   — fal.ai generates background (no text)
  07_overlay            — Pillow renders Arabic/Urdu via RAQM
"""
import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.agents.open_design_adapter import generate_open_design_variant
from app.tools.image_tools import render_product_showcase, render_infographic, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2
from app.utils.skill_rules import (
    anti_slop_rules, craft_polish_rules,
    artifact_composition_rules, responsive_layout_rules,
)

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

# ── Stage 05: Constrained Prompt Compiler ─────────────────────────────────────
# DeepSeek generates 3 candidate prompts, self-scores each, selects best 1-2.
# Cannot freestyle — all constraints from upstream stages are mandatory.

PROMPT_COMPILER_SYSTEM = """You are a fal.ai prompt compiler for a commercial marketing agency.
You are NOT allowed to freestyle. You MUST follow all constraints passed to you.

YOUR JOB:
1. Generate exactly 3 candidate prompts for the background image.
2. Self-score each on: constraint_compliance (0-100), novelty (0-100), anti_slop_risk (lower=better, 0-100).
3. Select the best 1-2 prompts only.
4. Write your reasoning.

HARD RULES (cannot be bypassed):
- Every prompt must start with [Format]: e.g. "Infographic: ..." or "Poster: ..."
- Every prompt must include brand palette hex values.
- Every prompt must end with: "no text, no letters, no numbers, no watermark, no typography"
- Every prompt must respect the text_safe_zones — that area must be clear for overlay.
- NEVER include Arabic, Urdu, or any text in the image prompt.
- Apply anti-slop negative prompts from the constraints.

Output ONLY valid JSON:
{
  "candidates": [
    {
      "id": "P1",
      "prompt": "...",
      "negative_prompt": "...",
      "scores": {"constraint_compliance": 0-100, "novelty": 0-100, "anti_slop_risk": 0-100},
      "reasoning": "..."
    }
  ],
  "selected": ["P1"],
  "selection_reasoning": "..."
}"""

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
        super().__init__(system_prompt=PROMPT_COMPILER_SYSTEM, tools=[], max_tokens=900)

    async def _compile_prompts(
        self,
        copy_en: str,
        copy_ar: str,
        visual_plan: dict,
        concept: dict,
        brand_colors: dict,
        brand_style: str,
        funnel_stage: str,
        brief: str,
        variant_label: str = "A",
    ) -> tuple[str, str]:
        """
        Stage 05: Compile 3 candidate prompts, self-score, return best (prompt, negative_prompt).
        """
        primary = brand_colors.get("primary", "#001A4D")
        accent  = brand_colors.get("accent",  "#4169E1")
        layout  = visual_plan.get("layout_family", concept.get("layout_family", "hero_stat"))
        style   = visual_plan.get("style_family", "premium_flat")
        no_go   = visual_plan.get("no_go_rules", [])
        text_zones = visual_plan.get("text_safe_zones", [])

        msg = (
            f"VARIANT: {variant_label}\n"
            f"FORMAT: {layout}\n"
            f"STYLE FAMILY: {style}\n"
            f"FUNNEL STAGE: {funnel_stage}\n"
            f"BRAND PALETTE: primary={primary}, accent={accent}\n"
            f"VISUAL STYLE: {brand_style}\n"
            f"TEXT SAFE ZONES: {json.dumps(text_zones)} — these areas must be CLEAR in the image\n"
            f"NO-GO RULES: {no_go}\n"
            f"BRIEF: {brief[:200]}\n"
            f"COPY CONTEXT (for art direction only — DO NOT put in prompt): AR={copy_ar[:60]} EN={copy_en[:60]}\n\n"
            f"--- ANTI-SLOP CONSTRAINTS ---\n{anti_slop_rules()}\n\n"
            f"--- CRAFT-POLISH ---\n{craft_polish_rules()}\n\n"
            f"--- ARTIFACT-COMPOSITION ---\n{artifact_composition_rules()}\n\n"
            f"--- RESPONSIVE-LAYOUT ---\n{responsive_layout_rules()}\n\n"
            "Generate 3 candidate prompts, self-score, select best. Return JSON only."
        )

        try:
            result = await self.run(msg, None)  # type: ignore
            decoder = json.JSONDecoder()
            start = result.find("{")
            if start >= 0:
                parsed, _ = decoder.raw_decode(result, start)
                selected_ids = parsed.get("selected", [])
                candidates = {c["id"]: c for c in parsed.get("candidates", [])}
                if selected_ids and selected_ids[0] in candidates:
                    best = candidates[selected_ids[0]]
                    return best.get("prompt", ""), best.get("negative_prompt", NEGATIVE_PROMPT)
        except Exception:
            pass

        # Fallback prompt if self-scoring fails
        fallback_prompt = (
            f"{layout.replace('_',' ').title()}: premium commercial marketing background, "
            f"{style.replace('_',' ')} aesthetic, brand color {primary} dominant, "
            f"accent {accent} highlights, clean {int(text_zones[0]['y_pct']*100) if text_zones else 45}% "
            f"bottom area clear for text overlay, no text, no letters, no watermark"
        )
        return fallback_prompt, NEGATIVE_PROMPT

    async def _get_bg_prompt(self, agent: BaseAgent, copy_en: str, brand_colors: dict,
                              brand_style: str, funnel_stage: str, brief: str) -> str:
        """Legacy wrapper — used when no visual_plan is available."""
        primary = brand_colors.get("primary", "#001A4D")
        accent  = brand_colors.get("accent",  "#4169E1")
        msg = (
            f"Generate a fal.ai background image prompt using this exact structure:\n"
            f"[format] + [subject] + [brand mood] + [palette hint] + "
            f"[composition with text-safe area bottom 45%] + [material/lighting] + [cleanliness constraints]\n\n"
            f"Brand context: {brand_style} | palette: primary {primary}, accent {accent}\n"
            f"Campaign: {copy_en[:80]}\n"
        )
        if brief:
            msg += f"Brand brief: {brief[:120]}\n"
        msg += (
            "\nOutput: ONE fal.ai prompt only, max 80 words. No text/letters/typography in image. "
            "Negative prompt not needed — just the positive prompt for the background."
        )
        try:
            p = await agent.run(msg, None)  # type: ignore
            return p.strip().strip('"').strip("'")
        except Exception:
            # Research-validated fallback formula
            return (
                f"Square premium wellness campaign background, modern healthcare brand aesthetic, "
                f"calm contemporary composition, palette influenced by brand blue {accent} "
                f"with soft ivory neutrals, clean negative space on the right side for Arabic "
                f"headline overlay, elegant layered depth, subtle product-ad feel, "
                f"no text, no letters, no watermark, no logo, no generic corporate portrait"
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

            # ── Stage 05: Constrained prompt compilation ──────────────────
            # Use visual_plan if available (from full 9-stage pipeline),
            # otherwise fall back to legacy _get_bg_prompt
            visual_plan_a = {
                "layout_family": "hero_stat",
                "style_family": "premium_flat",
                "text_safe_zones": [{"y_pct": 0.52, "label": "headline"}],
                "no_go_rules": ["no text in image", "no neon gradients", "no corporate portraits"],
            }
            visual_plan_b = {
                "layout_family": "bento_grid",
                "style_family": "minimal_data",
                "text_safe_zones": [{"y_pct": 0.45, "label": "metric"}],
                "no_go_rules": ["no text in image", "no generic icons", "no 3-column grids"],
            }
            bg_prompt_a, neg_a = await self._compile_prompts(
                copy_en, copy_ar, visual_plan_a, visual_plan_a, colors, style, "awareness", brief, "A"
            )
            bg_prompt_b, neg_b = await self._compile_prompts(
                copy_en, copy_ar, visual_plan_b, visual_plan_b, colors, style, "awareness", brief, "B"
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
                        negative_prompt=neg_a or NEGATIVE_PROMPT,
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
                        negative_prompt=neg_b or NEGATIVE_PROMPT,
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

            # ── Variant C: Open Design (runs only when OPEN_DESIGN_ENABLED=true) ──
            proj_name = (brand_mem.brand_voice or "")[:20].split()[0] if brand_mem and brand_mem.brand_voice else "Therapia"
            variant_c = await generate_open_design_variant(
                asset_id=asset_id,
                headline_ar=" ".join(copy_ar.split()[:6]) if copy_ar else copy_en[:50],
                subhead_ar=cta_ar[:40] if cta_ar else "",
                cta_ar=cta_ar[:25] if cta_ar else "",
                cta_en=cta_en[:25] if cta_en else "",
                brand_primary=primary,
                brand_accent=accent,
                channel=channel,
                width=w,
                height=h,
                upload_fn=upload_to_r2,
                project_name=proj_name or "Therapia",
            )

            primary_variant = variant_a if variant_a["status"] == "ok" else variant_b
            # Always include A+B; include C only if it ran (not skipped)
            variants = [variant_a, variant_b]
            if variant_c.get("status") not in ("skipped",):
                variants.append(variant_c)

            return {
                "design_url":      primary_variant.get("design_url"),
                "thumbnail_url":   primary_variant.get("thumbnail_url"),
                "variants":        variants,
                "memory_snapshot": memory_snapshot,
                "model_used":      "Pillow+fal.ai (A/B) + Open Design daemon (C)",
                "notes":           ["template-driven", "arabic-rtl-safe", "brand-controlled"],
            }
        except Exception as exc:
            return {
                "error": str(exc), "design_url": None, "thumbnail_url": None,
                "variants": [], "memory_snapshot": {}
            }
