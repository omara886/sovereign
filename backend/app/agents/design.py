"""
Design Agent — Two-layer architecture (non-negotiable):
  Layer 1: fal.ai generates BEAUTIFUL VISUAL SCENE — no text, no Arabic
  Layer 2: Pillow composites ALL text via Thmanyah font + arabic_reshaper

fal.ai cannot render Arabic. Never ask it to.
"""
import asyncio
import json
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.fal_tools import generate_image_fal
from app.agents.open_design_adapter import generate_open_design_variant
from app.tools.image_tools import composite_final_image, create_thumbnail
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.tools.r2_tools import upload_to_r2

# ── Visual scene prompts — Rich scenes, NOT dark gradients ────────────────────
# fal.ai only. No text. No Arabic. Layer 2 (Pillow) handles all text.

VISUAL_SCENE_PROMPTS = {
    "family_lifestyle": (
        "Warm lifestyle photography, Saudi family at home, mother checking child health on smartphone, "
        "soft natural lighting, modern Saudi interior, white and warm tones, "
        "professional health app promotional style, Apple Health aesthetic, "
        "bokeh background, genuine caring moment, high quality commercial photography, "
        "NO text, NO typography, NO Arabic script, NO Latin text anywhere in image, "
        "clean composition with visual breathing room on left third"
    ),
    "product_minimal": (
        "Clean minimal product visualization, smartphone floating on white background, "
        "purple gradient glow, health app UI visible on screen, "
        "geometric purple accent shapes, premium tech aesthetic, "
        "white and purple color scheme, Apple-style product photography, "
        "soft shadows, premium commercial quality, "
        "NO text, NO typography, NO writing of any kind anywhere, "
        "bottom 40% is lighter for text overlay"
    ),
    "empowerment_portrait": (
        "Confident young Saudi woman looking at phone with relief expression, "
        "modern Riyadh background softly blurred, warm professional lighting, "
        "purple and gold color accents in clothing or environment, "
        "health and wellness visual mood, empowerment feeling, "
        "high quality portrait photography commercial style, "
        "NO text, NO signs, NO Arabic or Latin writing anywhere visible"
    ),
    "abstract_health": (
        "Abstract health and wellness background, flowing purple and white organic shapes, "
        "geometric purple and gold gradient elements, "
        "clean modern minimal design aesthetic, premium brand visual, "
        "Saudi healthcare brand mood board style, "
        "smooth gradients, elegant composition, "
        "NO text, NO typography, NO words, NO letters of any kind, "
        "large clear area bottom half for text placement"
    ),
    "data_visualization": (
        "Data visualization aesthetic, purple and white color scheme, "
        "abstract flowing data streams, circular health metrics visualization, "
        "modern infographic background elements, premium fintech healthtech style, "
        "geometric patterns in purple and gold, "
        "clean professional background, "
        "NO text, NO numbers, NO Arabic, NO Latin characters, "
        "clear space on left 40% for Arabic text overlay"
    ),
}

PLATFORM_DIMS = {
    "instagram_post":    {"width": 1080, "height": 1080},
    "instagram_portrait":{"width": 1080, "height": 1350},
    "instagram_story":   {"width": 1080, "height": 1920},
    "linkedin_post":     {"width": 1200, "height": 627},
    "x_post":            {"width": 1600, "height": 900},
    "google_display":    {"width": 1200, "height": 628},
}

NEGATIVE_PROMPT = (
    "text, typography, words, letters, Arabic script, Latin script, numbers, "
    "watermark, signature, caption, logo, brand name, "
    "neon gradients, floating particles, cluttered, busy"
)

OPENCODESIGN_PRINCIPLES = [
    "Layer 1: fal.ai — beautiful visual scene, no text",
    "Layer 2: Pillow — Thmanyah Arabic + RTL + brand colors",
    "arabic_reshaper + bidi — correct glyph shaping",
    "Brand logo composited from brand_memory.logo_url",
    "Full copy_ar — no truncation",
]


class DesignAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt="You are an art director.", tools=[], max_tokens=50)

    def _build_memory_snapshot(self, brand_mem, project_mem, channel: str) -> dict:
        snap: dict = {"channel": channel}
        if brand_mem:
            snap["brand_voice"]   = bool(brand_mem.brand_voice)
            snap["colors"]        = bool(brand_mem.color_palette)
            snap["dos"]           = len(brand_mem.dos or [])
            snap["is_provisional"]= brand_mem.is_provisional
        if project_mem:
            snap["brand_brief"]   = bool(getattr(project_mem, "brand_brief", None))
            snap["icp"]           = bool(project_mem.icp)
            snap["tone"]          = bool(project_mem.tone)
            snap["approved"]      = len(project_mem.approved_examples or [])
            snap["rejected"]      = len(project_mem.rejected_examples or [])
        return snap

    async def generate_design(
        self,
        db: AsyncSession,
        project_id: str,
        asset_id: str,
        channel: str,
        copy_ar: str,
        copy_en: str,
        cta_ar: str = "",
        cta_en: str = "",
        num_variants: int = 1,
    ) -> dict:
        try:
            brand_mem   = await get_brand_memory(db, project_id)
            project_mem = await get_project_memory(db, project_id)

            colors  = (brand_mem.color_palette or {}) if brand_mem else {}
            primary = colors.get("primary", "#4C1D95")
            accent  = colors.get("accent",  "#F59E0B")
            brand_colors = {"primary": primary, "accent": accent}

            # Fetch logo
            logo_bytes: bytes | None = None
            logo_url = (brand_mem.logo_url or "") if brand_mem else ""
            if logo_url and logo_url.startswith("http"):
                try:
                    import httpx as _hx
                    async with _hx.AsyncClient(timeout=8) as _c:
                        _r = await _c.get(logo_url)
                        if _r.status_code == 200:
                            logo_bytes = _r.content
                except Exception:
                    pass
            elif logo_url.startswith("data:"):
                try:
                    import base64 as _b64
                    logo_bytes = _b64.b64decode(logo_url.split(",", 1)[1])
                except Exception:
                    pass

            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            dims = PLATFORM_DIMS.get(platform_key, {"width": 1080, "height": 1080})
            w, h = dims["width"], dims["height"]

            memory_snapshot = self._build_memory_snapshot(brand_mem, project_mem, channel)

            # ── Variant A: flux/dev + family/lifestyle scene ────────────────
            async def _make_variant_a() -> dict:
                try:
                    scene_key = random.choice(["family_lifestyle", "empowerment_portrait"])
                    scene_prompt = VISUAL_SCENE_PROMPTS[scene_key]
                    bg = await generate_image_fal(
                        scene_prompt, "fal-ai/flux/dev", w, h,
                        negative_prompt=NEGATIVE_PROMPT,
                    )
                    final_img = await asyncio.to_thread(
                        composite_final_image,
                        bg, copy_ar, copy_en, cta_ar,
                        brand_colors, logo_bytes, w, h,
                    )
                    thumb = await create_thumbnail(final_img)
                    vid = f"{asset_id}_vA"
                    durl = await upload_to_r2(final_img, f"{vid}.jpg", "image/jpeg")
                    turl = await upload_to_r2(thumb, f"{vid}_thumb.jpg", "image/jpeg")
                    return {
                        "variant": "A", "label": "Campaign Visual",
                        "description": f"flux/dev scene ({scene_key}) + Thmanyah Arabic overlay",
                        "design_url": durl, "thumbnail_url": turl,
                        "scene_concept": scene_key, "status": "ok",
                        "source": "flux/dev+pillow",
                        "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                    }
                except BaseException as exc:
                    return {"variant": "A", "label": "Campaign Visual",
                            "error": str(exc), "status": "failed"}

            # ── Variant B: Ideogram v2 + data/abstract scene ────────────────
            async def _make_variant_b() -> dict:
                try:
                    scene_key = random.choice(["abstract_health", "data_visualization", "product_minimal"])
                    scene_prompt = VISUAL_SCENE_PROMPTS[scene_key]
                    bg = await generate_image_fal(
                        scene_prompt, "fal-ai/ideogram/v2", w, h,
                        negative_prompt=NEGATIVE_PROMPT,
                    )
                    final_img = await asyncio.to_thread(
                        composite_final_image,
                        bg, copy_ar, copy_en, cta_ar,
                        brand_colors, logo_bytes, w, h,
                    )
                    thumb = await create_thumbnail(final_img)
                    vid = f"{asset_id}_vB"
                    durl = await upload_to_r2(final_img, f"{vid}.jpg", "image/jpeg")
                    turl = await upload_to_r2(thumb, f"{vid}_thumb.jpg", "image/jpeg")
                    return {
                        "variant": "B", "label": "Infographic",
                        "description": f"Ideogram v2 scene ({scene_key}) + Thmanyah Arabic overlay",
                        "design_url": durl, "thumbnail_url": turl,
                        "scene_concept": scene_key, "status": "ok",
                        "source": "ideogram/v2+pillow",
                        "opencodesign_principles": OPENCODESIGN_PRINCIPLES,
                    }
                except BaseException as exc:
                    return {"variant": "B", "label": "Infographic",
                            "error": str(exc), "status": "failed"}

            variant_a = await _make_variant_a()
            variant_b = await _make_variant_b()

            # ── Variant C: Open Design ──────────────────────────────────────
            variant_c = await generate_open_design_variant(
                asset_id=asset_id,
                headline_ar=copy_ar,
                subhead_ar=copy_en[:60] if copy_en else "",
                cta_ar=cta_ar[:30] if cta_ar else "",
                cta_en=cta_en[:30] if cta_en else "",
                brand_primary=primary,
                brand_accent=accent,
                channel=channel,
                width=w, height=h,
                upload_fn=upload_to_r2,
                project_name="Therapia",
            )

            primary_variant = variant_a if variant_a["status"] == "ok" else variant_b
            variants = [variant_a, variant_b]
            if variant_c.get("status") not in ("skipped",):
                variants.append(variant_c)

            return {
                "design_url":      primary_variant.get("design_url"),
                "thumbnail_url":   primary_variant.get("thumbnail_url"),
                "variants":        variants,
                "memory_snapshot": memory_snapshot,
                "model_used":      "A: flux/dev | B: ideogram/v2 | C: open-design",
                "notes":           ["two-layer: fal.ai scene + pillow arabic overlay"],
            }
        except Exception as exc:
            return {
                "error": str(exc),
                "design_url": None, "thumbnail_url": None,
                "variants": [], "memory_snapshot": {},
            }
