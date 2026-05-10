import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, HAIKU
from app.tools.fal_tools import generate_image_fal
from app.tools.image_tools import apply_text_overlay, create_thumbnail, resize_image
from app.tools.memory_tools import get_brand_memory
from app.tools.r2_tools import upload_to_r2

SYSTEM_PROMPT = """You are the Design Agent for Sovereign. You generate professional marketing visuals using fal.ai.

ALWAYS read BrandMemory first. Brand rules are law.

If the brand has an uploaded logo (logo_url), reference it in the fal.ai prompt: "incorporate brand logo style" and use brand colors exactly.
If the brand has uploaded screenshots, use them as style reference for the visual direction.
If an Arabic font is uploaded (arabic_font_url), the text overlay will use it automatically.

Image generation process:
1. Read brand memory — get colors, visual_style, image_style, logo_url, arabic_font_url, templates
2. Build fal.ai prompt: encode brand colors, visual style, mood. Always add "No text in image — leave 40% clear space at bottom for text overlay. Professional quality."
3. Choose model: fal-ai/flux-pro for ad creatives, fal-ai/flux/schnell for social posts
4. Call generate_image with prompt and platform dimensions
5. Call apply_text_and_upload with Arabic + English copy
6. Return design_url and thumbnail_url

Platform dimensions (exact):
- instagram_post: 1080x1080
- instagram_story: 1080x1920
- linkedin_post: 1200x627
- x_post: 1600x900
- google_display: 1200x628

Text overlay rules:
- Arabic text: RTL direction, minimum 48px headline, 28px body
- Leave 15% padding from edges
- Contrast minimum 4.5:1 (WCAG AA)
- Arabic on top (larger), English below (smaller) for bilingual

If brand colors are provisional, use them but note in design_notes: "Colors provisional — approval pending"

Output JSON: {"design_url": "...", "thumbnail_url": "...", "fal_prompt": "...", "model_used": "...", "notes": []}"""

TOOLS = [
    {
        "name": "get_brand_memory",
        "description": "Get brand memory for colors, fonts, visual style",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "generate_image",
        "description": "Generate image using fal.ai",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "model": {"type": "string", "enum": ["fal-ai/flux-pro", "fal-ai/flux/schnell"]},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
            "required": ["prompt", "model", "width", "height"],
        },
    },
    {
        "name": "apply_text_and_upload",
        "description": "Apply text overlay to image bytes and upload to R2. Returns design_url and thumbnail_url.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_key": {"type": "string", "description": "Key from generate_image result"},
                "copy_ar": {"type": "string"},
                "copy_en": {"type": "string"},
                "cta_ar": {"type": "string"},
                "cta_en": {"type": "string"},
                "asset_id": {"type": "string"},
            },
            "required": ["image_key", "asset_id"],
        },
    },
]

_IMAGE_STORE: dict[str, bytes] = {}

PLATFORM_DIMENSIONS = {
    "instagram_post": (1080, 1080),
    "instagram_story": (1080, 1920),
    "linkedin_post": (1200, 627),
    "x_post": (1600, 900),
    "google_display": (1200, 628),
}


class DesignAgent(BaseAgent):
    MODEL = HAIKU  # just builds an fal.ai prompt + calls tools — no deep reasoning needed

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=2048)
        self.tool_implementations = {
            "get_brand_memory": self._get_brand_memory,
            "generate_image": self._generate_image,
            "apply_text_and_upload": self._apply_text_and_upload,
        }

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {
            "color_palette": mem.color_palette,
            "typography": mem.typography,
            "visual_style": mem.visual_style,
            "image_style": mem.image_style,
            "brand_voice": mem.brand_voice,
            "logo_url": mem.logo_url,
            "arabic_font_url": mem.arabic_font_url,
            "templates": mem.templates,  # includes screenshots + other uploaded assets
            "dos": mem.dos,
            "donts": mem.donts,
            "is_provisional": mem.is_provisional,
        }

    async def _generate_image(self, db: AsyncSession, prompt: str, model: str, width: int, height: int) -> dict:
        image_bytes = await generate_image_fal(prompt, model, width, height)
        key = str(uuid.uuid4())
        _IMAGE_STORE[key] = image_bytes
        return {"image_key": key, "width": width, "height": height}

    async def _apply_text_and_upload(
        self,
        db: AsyncSession,
        image_key: str,
        asset_id: str,
        copy_ar: str = "",
        copy_en: str = "",
        cta_ar: str = "",
        cta_en: str = "",
    ) -> dict:
        image_bytes = _IMAGE_STORE.get(image_key)
        if not image_bytes:
            return {"error": "image_key not found"}
        text_ar = f"{copy_ar}\n{cta_ar}".strip() if copy_ar or cta_ar else ""
        text_en = f"{copy_en}\n{cta_en}".strip() if copy_en or cta_en else ""
        with_text = await apply_text_overlay(image_bytes, text_ar, text_en)
        thumb = await create_thumbnail(with_text)
        design_url = await upload_to_r2(with_text, f"{asset_id}.png", "image/png")
        thumbnail_url = await upload_to_r2(thumb, f"{asset_id}_thumb.png", "image/png")
        _IMAGE_STORE.pop(image_key, None)
        return {"design_url": design_url, "thumbnail_url": thumbnail_url}

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
    ) -> dict:
        """
        Direct deterministic pipeline — no Claude needed for design generation.
        Claude was causing rate limit failures mid-loop, leaving thumbnails as None.
        """
        try:
            platform_key = channel.replace("-", "_").replace(" ", "_") + "_post"
            dims = PLATFORM_DIMENSIONS.get(platform_key, (1080, 1080))

            # 1. Get brand memory for fal.ai prompt
            brand_mem = await get_brand_memory(db, project_id)
            colors = (brand_mem.color_palette or {}) if brand_mem else {}
            style = (brand_mem.visual_style or "clean, professional, dark background") if brand_mem else "clean, professional"
            primary = colors.get("primary", "#0A0A0A")
            accent = colors.get("accent", "#C9A84C")

            fal_prompt = (
                f"Professional marketing visual. {style}. "
                f"Color palette: primary {primary}, accent {accent}. "
                f"Dark background. No text in image — leave 40% clear space at bottom for text overlay. "
                f"High quality, {dims[0]}x{dims[1]}px."
            )

            # 2. Generate image
            image_bytes = await generate_image_fal(fal_prompt, "fal-ai/flux/schnell", dims[0], dims[1])

            # 3. Apply text overlay
            text_ar = f"{copy_ar}\n{cta_ar}".strip() if copy_ar or cta_ar else ""
            text_en = f"{copy_en}\n{cta_en}".strip() if copy_en or cta_en else ""
            with_text = await apply_text_overlay(image_bytes, text_ar, text_en)

            # 4. Create thumbnail and upload both
            thumb = await create_thumbnail(with_text)
            design_url = await upload_to_r2(with_text, f"{asset_id}.png", "image/png")
            thumbnail_url = await upload_to_r2(thumb, f"{asset_id}_thumb.jpg", "image/jpeg")

            return {
                "design_url": design_url,
                "thumbnail_url": thumbnail_url,
                "fal_prompt": fal_prompt,
                "model_used": "fal-ai/flux/schnell",
                "notes": ["provisional" if (brand_mem and brand_mem.is_provisional) else "approved brand"],
            }
        except Exception as exc:
            return {"error": str(exc), "design_url": None, "thumbnail_url": None}
