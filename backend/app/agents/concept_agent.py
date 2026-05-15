"""
Stage 02 — Concept Agent.
Generates 3-5 distinct concept options for the campaign.
Each concept has: format, message angle, persuasion framework, narrative arc, score.
Blocks on weak concepts (all score < 60).
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.utils.skill_rules import content_engine_rules, marketing_psychology_rules

SYSTEM_PROMPT = """You are the Concept Director for a premium marketing agency.
You generate 3-5 DISTINCT creative concepts for an infographic or visual campaign.

CRITICAL RULES:
1. Each concept must use a DIFFERENT persuasion framework (PAS, AIDA, loss-aversion, social-proof, authority).
2. Each concept must use a DIFFERENT layout_family (never repeat the same grid structure).
3. Each concept must tell a DIFFERENT story angle — not just different styling of the same message.
4. Score each concept honestly. If all score below 60, say so and explain why.
5. Output ONLY valid JSON. No text outside JSON.

Output schema:
{
  "concepts": [
    {
      "id": "C1",
      "format": "stat_card|infographic_bento|vertical_flow|poster_hero|carousel|ui_mock",
      "layout_family": "hero_stat|bento_grid|vertical_flow|comparison|timeline|poster_hero",
      "persuasion_framework": "PAS|AIDA|loss_aversion|social_proof|authority",
      "story_angle": "<one sentence describing the unique narrative>",
      "hero_element": "<the single most powerful visual/stat element>",
      "narrative_arc": ["beat1", "beat2", "beat3"],
      "why_distinct": "<why this is different from the others>",
      "scores": {
        "novelty": 0-100,
        "clarity": 0-100,
        "funnel_fit": 0-100,
        "brand_fit": 0-100,
        "overall": 0-100
      }
    }
  ],
  "recommended": ["C1", "C2"],
  "block_reason": null
}
If all concepts score below 60, set block_reason to explain why and set recommended to []."""


class ConceptAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=1200)

    async def generate_concepts(
        self,
        db: AsyncSession,
        project_id: str,
        strategy: dict,
        existing_assets_summary: list[str] | None = None,
    ) -> dict:
        from app.tools.memory_tools import get_brand_memory, get_project_memory
        brand_mem = await get_brand_memory(db, project_id)
        project_mem = await get_project_memory(db, project_id)
        brief_doc = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

        novelty_context = ""
        if existing_assets_summary:
            novelty_context = (
                f"RECENTLY USED LAYOUTS (must NOT repeat these): {existing_assets_summary}\n"
            )

        msg = (
            f"STRATEGY:\n{json.dumps(strategy, ensure_ascii=False)}\n\n"
            f"BRAND BRIEF (excerpt):\n{brief_doc[:400]}\n\n"
            f"{novelty_context}"
            f"CONTENT-ENGINE RULES:\n{content_engine_rules()}\n\n"
            f"MARKETING-PSYCHOLOGY:\n{marketing_psychology_rules()}\n\n"
            "Generate 3-5 distinct concepts. Return JSON only."
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

        return {
            "concepts": [],
            "recommended": [],
            "block_reason": f"Concept agent failed to parse: {result[:200]}",
        }
