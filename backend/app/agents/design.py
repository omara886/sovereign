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

THERAPIA_DNA = {
    "brand": "Therapia",
    "visual_principles": [
        "calm not sleepy",
        "Saudi contemporary",
        "premium wellness not hospital",
        "human privacy no exaggeration",
    ],
    "approved_locations": [
        "Riyadh apartment morning",
        "Saudi office lounge",
        "modern family living room",
        "private consultation room",
        "youth study desk at blue hour",
    ],
    "materials": ["linen", "ceramic", "limestone", "walnut", "brass", "frosted glass", "fabric", "dark wood"],
    "lighting": [
        "soft Riyadh sunrise through sheer curtains",
        "warm evening lamp light",
        "blue hour window",
        "late afternoon golden office glass",
    ],
    "palette": {"primary": "#0F3D3E", "secondary": "#D7B98E", "accent_hint": "deep green reflection"},
    "camera": [
        "50mm lens",
        "85mm lens",
        "35mm lens",
        "shallow depth of field",
        "realistic premium commercial editorial photography",
    ],
    "avoid": [
        "hospital",
        "sad patient",
        "generic wellness",
        "Western therapy cliché",
        "camels",
        "random desert",
        "random mosque",
        "doctor coat",
        "therapy couch",
    ],
}

FUNNEL_SCENE_TEMPLATES = {
    "awareness": {
        "description": "Brand impression, emotional, no offer",
        "visual_territory": "centered statement or architectural negative space",
        "scene": "A quiet morning corner in a contemporary Riyadh apartment. A phone rests face-down beside a ceramic Arabic coffee cup, folded notebook, soft linen, and small brass lamp. No people. Calm private atmosphere suggesting online therapy just happened.",
        "saudi_context": "Modern Saudi home, limestone wall, subtle Najdi-inspired shadow pattern, warm hospitality objects, no clichés, no desert, no camels, no mosque.",
        "composition": "4:5 vertical. Main visual weight lower-left. Natural negative space upper-right created by sunlit wall texture, curtain shadow, and warm light falloff. Negative space must feel photographic not empty.",
        "lighting": "Soft Riyadh sunrise through sheer curtains, warm highlights, gentle shadows.",
        "materials": "limestone, ceramic, linen, walnut, brushed brass",
        "palette": "Warm ivory, sand, muted clay, date brown, deep green accent only as small reflection.",
        "camera": "50mm lens, shallow depth of field, editorial commercial photography, tactile realism, natural grain.",
        "layout_pattern": "architectural_negative_space",
    },
    "consideration": {
        "description": "Show product in context, build trust",
        "visual_territory": "editorial lifestyle or luxury still life",
        "scene": "An elegant Saudi living room after dinner. Two Arabic coffee cups on a side table, soft throw blanket, phone placed near edge, warm lamp in background. Scene feels calm family home, private.",
        "saudi_context": "Contemporary majlis-inspired living room, modern Saudi luxury, subtle geometric wall shadow, warm hospitality, no tourist clichés.",
        "composition": "4:5 vertical. Foreground detail lower-right. Natural negative space upper-left from warm wall texture and soft shadow. Objects frame the empty zone naturally.",
        "lighting": "Evening indoor light, lamp glow, soft falloff, warm but not yellow.",
        "materials": "fabric, ceramic, brass, dark wood, stone",
        "palette": "Cream, date brown, muted gold, stone gray, deep green accent.",
        "camera": "65mm lens, close editorial still life, realistic texture, premium advertising photography.",
        "layout_pattern": "object_framed",
    },
    "conversion": {
        "description": "Clear offer, clear CTA, action now",
        "visual_territory": "architectural negative space for clean composition",
        "scene": "A refined private consultation room represented through objects only: comfortable chair edge, tissue box, water glass, notebook, phone, soft lamp, textured wall. No doctor, no patient.",
        "saudi_context": "Contemporary Saudi wellness interior, subtle Gulf hospitality design, premium privacy, believable professional setting.",
        "composition": "1:1 square. Objects arranged right half. Natural negative space left third created by softly lit textured wall and plant shadow.",
        "lighting": "Warm evening lamp light, gentle ambient fill, premium contrast.",
        "materials": "stone, linen, ceramic, frosted glass, dark wood",
        "palette": "Ivory, warm beige, olive-gray, terracotta, soft dark green.",
        "camera": "85mm lens, low angle, shallow depth of field, luxury healthcare still life photography.",
        "layout_pattern": "glass_card",
    },
    "retention": {
        "description": "Warmth, belonging, ongoing relationship",
        "visual_territory": "quiet recovery or family warmth",
        "scene": "A teenager's study desk in a Saudi home at blue hour. Headphones, closed journal, school materials with no readable text, desk lamp, phone resting face-down. Room feels safe and lived-in.",
        "saudi_context": "Modern Saudi family home, realistic study setup, subtle Arabic books on shelf but no readable text, contemporary youth environment.",
        "composition": "9:16 story layout. Desk objects in bottom-right. Natural negative space in top-left created by dim wall, shelf blur, and lamp falloff.",
        "lighting": "Warm desk lamp mixed with blue hour window light, cinematic but realistic.",
        "materials": "wood desk, paper, matte headphones, soft fabric, glass",
        "palette": "Warm walnut, cream, muted navy, soft green accent.",
        "camera": "35mm lens, slight overhead crop, editorial lifestyle photography, realistic commercial finish.",
        "layout_pattern": "editorial_side",
    },
}

GLOBAL_NEGATIVE_PROMPT = (
    "plain gradient, empty background, dark bottom gradient, black overlay, "
    "generic stock photo, corporate template, Canva template, 2010 social media ad, "
    "fake premium, overused bokeh, plastic skin, over-smoothed faces, "
    "fake Arabic text, gibberish letters, readable text, watermark, logo, poster mockup, "
    "app UI, distorted hands, extra fingers, duplicated people, uncanny face, "
    "random mosque, camel, desert stereotype, tourist cliché, "
    "doctor coat, hospital bed, therapy couch cliché, sad crying person, exaggerated emotion, "
    "low resolution, blurry, overexposed, underexposed, excessive glow, cheap neon"
)


def compile_scene_prompt(funnel_stage: str, brand_dna: dict, platform: str) -> str:
    """Compile 11-part premium prompt from brand DNA + funnel stage."""
    template = FUNNEL_SCENE_TEMPLATES.get(funnel_stage, FUNNEL_SCENE_TEMPLATES["consideration"])
    ratio_map = {
        "instagram_post": "1:1 square",
        "instagram_portrait": "4:5 vertical",
        "instagram_story": "9:16 vertical story",
        "linkedin_post": "1.91:1 horizontal",
        "x_post": "16:9 horizontal",
    }
    ratio = ratio_map.get(platform, "4:5 vertical")

    return (
        "Premium commercial campaign image for Therapia, a Saudi digital mental wellness app. "
        f"Strategic idea: {template['description']}. "
        f"Scene: {template['scene']} "
        f"Saudi authenticity: {template['saudi_context']} "
        f"Composition: {ratio} editorial layout. {template['composition']} "
        f"Lighting: {template['lighting']} "
        f"Materials: {template['materials']}. "
        f"Palette: {template['palette']} "
        f"Camera: {template['camera']}. "
        "Quality: Apple-level restraint, premium wellness brand, emotionally intelligent, cinematic but believable. "
        "NO text, NO logo, NO watermark, NO fake Arabic letters, NO app UI, NO hospital, NO doctor, NO sad patient, NO therapy couch cliché."
    )

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
