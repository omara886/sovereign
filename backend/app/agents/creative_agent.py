"""
Creative Agent — decides HOW to make the asset.

Inputs: marketing-agent decision JSON + brand memory.
Output: art direction JSON + generation-ready fal.ai prompt (NO Arabic text in prompt).

Rules:
- Prompt must be format-first: "[Format]: [style] [composition] [subject] [palette] [exclusions]"
- Must include text_safe_zones with percentage coordinates
- Must include NEGATIVE_PROMPT block
- Arabic copy goes in post_process_steps only, never in the generation prompt
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory


SYSTEM_PROMPT = """You are a Creative Director Agent. You design the art direction and write a generation-ready prompt for a marketing asset.

You output only valid JSON. No explanation outside the JSON.

Rules:
1. generation_prompt must be format-first: "[Format]: [style] [composition] [subject] [palette hint] [text-safe zone instruction] [negative constraints]"
2. generation_prompt must NOT contain any Arabic text, headlines, or CTA copy.
3. generation_prompt must include: "no text, no letters, no watermark, reserve [position] text-safe area"
4. text_safe_zones must be defined as percentage coordinates of the canvas.
5. post_process_steps must include Arabic rendering method.
6. Negative prompt must include the standard blacklist.

Output schema:
{
  "art_family": "premium_editorial|flat_product|3d_soft|mascot|infographic_modular",
  "style_tokens": ["..."],
  "composition_template": "<name>",
  "text_safe_zones": [{"label":"headline", "x_pct":0.5, "y_pct":0.6, "w_pct":0.8, "h_pct":0.25}],
  "generation_parts": {"background": true, "illustration": false, "photo": true},
  "generation_prompt": "<long prompt — format-first, no Arabic, no text>",
  "negative_prompt": "photorealistic man, businessman, stock photo, plastic skin, HDR face, neon purple-blue gradient, floating particles, giant text, watermark, logo soup, random glyphs, broken letters, arabic letters in image, latin letters",
  "post_process_steps": ["compose_arabic_RAQM_preferred", "CTA_pill_brand_token", "contrast_check_WCAG_AA"],
  "assets_to_export": [
    {"name":"master","width":1080,"height":1080},
    {"name":"instagram_feed","width":1080,"height":1080},
    {"name":"instagram_story","width":1080,"height":1920},
    {"name":"linkedin","width":1200,"height":627}
  ]
}"""


NEGATIVE_STANDARD = (
    "photorealistic man, businessman in suit, shemagh portrait, stock photo, "
    "plastic skin, HDR face, shallow depth of field, cinematic portrait, "
    "neon blue purple gradient, glowing particles, generic corporate photography, "
    "giant text, random glyphs, broken letters, arabic letters in image, latin letters, "
    "watermark, signature, cluttered layout, cheap ad template, social media ad template, "
    "oversized text, dominant typography, text covering subject, logo soup"
)


class CreativeAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=800)

    async def direct(
        self,
        db: AsyncSession,
        project_id: str,
        marketing_decision: dict,
        copy_ar: str = "",
        copy_en: str = "",
    ) -> dict:
        brand_mem = await get_brand_memory(db, project_id)
        project_mem = await get_project_memory(db, project_id)
        brief_doc = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

        colors = (brand_mem.color_palette or {}) if brand_mem else {}
        primary = colors.get("primary", "#001A4D")
        accent = colors.get("accent", "#4169E1")
        style = (brand_mem.visual_style or "commercial app-marketing") if brand_mem else "commercial"

        context = (
            f"MARKETING DECISION:\n{json.dumps(marketing_decision, ensure_ascii=False)}\n\n"
            f"BRAND BRIEF (first 300 chars):\n{brief_doc[:300]}\n\n"
            f"BRAND COLORS: primary={primary}, accent={accent}\n"
            f"VISUAL STYLE: {style}\n"
            f"COPY CONTEXT (for art direction only — do NOT include in prompt): AR={copy_ar[:60]} EN={copy_en[:60]}\n"
            f"STANDARD NEGATIVE PROMPT: {NEGATIVE_STANDARD}\n"
            "Return the creative direction JSON only."
        )
        result = await self.run(context, db)
        decoder = json.JSONDecoder()
        start = result.find("{")
        if start >= 0:
            try:
                parsed, _ = decoder.raw_decode(result, start)
                # Enforce negative prompt is always present
                if "negative_prompt" not in parsed or not parsed["negative_prompt"]:
                    parsed["negative_prompt"] = NEGATIVE_STANDARD
                return parsed
            except json.JSONDecodeError:
                pass
        return {
            "art_family": "premium_editorial",
            "generation_prompt": (
                f"Premium campaign poster background, modern wellness brand aesthetic, "
                f"calm composition, palette influenced by {accent} accent with soft neutrals, "
                f"clean right-side negative space for Arabic headline overlay, "
                f"no text, no letters, no watermark, no corporate portrait"
            ),
            "negative_prompt": NEGATIVE_STANDARD,
            "text_safe_zones": [{"label": "headline", "x_pct": 0.5, "y_pct": 0.6, "w_pct": 0.85, "h_pct": 0.3}],
            "post_process_steps": ["compose_arabic_RAQM_preferred", "CTA_pill_brand_token"],
            "assets_to_export": [
                {"name": "instagram_feed", "width": 1080, "height": 1080},
                {"name": "instagram_story", "width": 1080, "height": 1920},
            ],
        }
