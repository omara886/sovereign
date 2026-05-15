"""
Stage 04 — Visual Plan Agent.
ALL Open CoDesign skills applied here as hard constraints, not decoration.
Produces visual_plan.json: layout, panels, text_safe_zones, style_family, brand_tokens.
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.utils.skill_rules import (
    artifact_composition_rules,
    responsive_layout_rules,
    anti_slop_rules,
    craft_polish_rules,
    editorial_typography_rules,
)

SYSTEM_PROMPT = """You are the Art Director for a premium marketing agency.
You produce a concrete visual plan that constrains ALL downstream generation.
The image model (fal.ai) and overlay pipeline MUST follow your plan exactly.

RULES:
1. Every panel must have a role: hero|stat|proof|CTA|background.
2. text_safe_zones must cover all Arabic/Urdu text — no text in the generated image.
3. no_go_rules must include ALL items from the anti-slop blacklist relevant to this concept.
4. style_family must be specific, not generic. Choose: premium_flat|minimal_data|playful_brand|cultural_commercial|editorial_magazine|data_viz_clean
5. brand_tokens must come from brand memory — no invented colors.
6. Output ONLY valid JSON."""

VISUAL_PLAN_SCHEMA = """{
  "layout_family": "...",
  "panels": [
    {"id":"hero","role":"hero","x_pct":0.0,"y_pct":0.0,"w_pct":1.0,"h_pct":0.55,"content":"background scene only"},
    {"id":"text_zone","role":"stat","x_pct":0.07,"y_pct":0.55,"w_pct":0.86,"h_pct":0.35,"content":"Arabic headline + subhead overlay"}
  ],
  "language": "ar|ur|bilingual",
  "text_safe_zones": [{"label":"headline","x_pct":0.07,"y_pct":0.56,"w_pct":0.86,"h_pct":0.22,"anchor":"right"}],
  "no_go_rules": ["no text in generated image","no neon gradients","..."],
  "style_family": "premium_flat",
  "brand_tokens": {"accent_hex":"#4169E1","background_hex":"#001A4D","typeface_ar":"Thmanyah Sans","typeface_en":"Inter"},
  "composition_reasoning": "<why this layout serves the concept>"
}"""


class VisualPlanAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=800)

    async def plan(
        self,
        db: AsyncSession,
        project_id: str,
        concept: dict,
        copy_blocks: dict,
        language: str = "ar",
    ) -> dict:
        from app.tools.memory_tools import get_brand_memory
        brand_mem = await get_brand_memory(db, project_id)
        colors = (brand_mem.color_palette or {}) if brand_mem else {}
        primary = colors.get("primary", "#001A4D")
        accent  = colors.get("accent",  "#4169E1")

        msg = (
            f"CONCEPT:\n{json.dumps(concept, ensure_ascii=False)}\n\n"
            f"COPY BLOCKS (for safe-zone sizing):\n{json.dumps(copy_blocks, ensure_ascii=False)}\n\n"
            f"BRAND COLORS: primary={primary}, accent={accent}\n\n"
            f"--- ARTIFACT-COMPOSITION RULES ---\n{artifact_composition_rules()}\n\n"
            f"--- ANTI-SLOP BLACKLIST ---\n{anti_slop_rules()}\n\n"
            f"--- CRAFT-POLISH ---\n{craft_polish_rules()}\n\n"
            f"--- EDITORIAL-TYPOGRAPHY ({language.upper()}) ---\n{editorial_typography_rules(language)}\n\n"
            f"--- RESPONSIVE-LAYOUT ---\n{responsive_layout_rules()}\n\n"
            f"OUTPUT SCHEMA:\n{VISUAL_PLAN_SCHEMA}\n\n"
            "Produce the visual_plan JSON. No text outside JSON."
        )

        result = await self.run(msg, db)
        decoder = json.JSONDecoder()
        start = result.find("{")
        if start >= 0:
            try:
                parsed, _ = decoder.raw_decode(result, start)
                return parsed
            except json.JSONDecodeError:
                pass

        # Fallback — safe default plan
        return {
            "layout_family": concept.get("layout_family", "hero_stat"),
            "panels": [
                {"id": "bg", "role": "background", "x_pct": 0.0, "y_pct": 0.0, "w_pct": 1.0, "h_pct": 1.0, "content": "background only"},
                {"id": "text", "role": "hero", "x_pct": 0.07, "y_pct": 0.52, "w_pct": 0.86, "h_pct": 0.38, "content": "Arabic overlay"},
            ],
            "language": language,
            "text_safe_zones": [{"label": "headline", "x_pct": 0.07, "y_pct": 0.53, "w_pct": 0.86, "h_pct": 0.25, "anchor": "right"}],
            "no_go_rules": ["no text in generated image", "no neon gradients", "no corporate portraits", "no watermarks"],
            "style_family": "premium_flat",
            "brand_tokens": {"accent_hex": accent, "background_hex": primary, "typeface_ar": "Thmanyah Sans", "typeface_en": "Inter"},
            "composition_reasoning": "fallback plan",
        }
