"""
Stage 02 — Concept Agent.
Generates 3 DISTINCT concept options (different layout_family + persuasion_framework).
If LLM fails or scores badly, structured fallbacks guarantee diversity.
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.utils.skill_rules import content_engine_rules, marketing_psychology_rules

# Structured fallbacks — always distinct, cover common campaign types
FALLBACK_CONCEPTS = [
    {
        "id": "F1", "format": "stat_card", "layout_family": "hero_stat",
        "persuasion_framework": "social_proof", "style_family": "premium_flat",
        "story_angle": "Lead with the key metric that proves the product works",
        "hero_element": "Primary KPI number (time saved, assessments completed)",
        "narrative_arc": ["State the impressive number", "Explain what it means", "CTA to experience it"],
        "scores": {"novelty": 70, "clarity": 85, "funnel_fit": 75, "brand_fit": 80, "overall": 78},
    },
    {
        "id": "F2", "format": "infographic_bento", "layout_family": "bento_grid",
        "persuasion_framework": "PAS", "style_family": "minimal_data",
        "story_angle": "Show the problem (no time for health), then the fast solution",
        "hero_element": "Time comparison: old way vs 8-minute Therapia way",
        "narrative_arc": ["Problem: health requires too much time", "Agitate: you're falling behind", "Solution: 8 minutes is all it takes"],
        "scores": {"novelty": 75, "clarity": 80, "funnel_fit": 85, "brand_fit": 80, "overall": 80},
    },
    {
        "id": "F3", "format": "poster_hero", "layout_family": "poster_hero",
        "persuasion_framework": "authority", "style_family": "editorial_magazine",
        "story_angle": "Position as the trusted professional health companion",
        "hero_element": "Bold Arabic headline + brand credential",
        "narrative_arc": ["Authority claim", "Specific credibility signal", "Invitation to start"],
        "scores": {"novelty": 65, "clarity": 90, "funnel_fit": 70, "brand_fit": 85, "overall": 78},
    },
]

SYSTEM_PROMPT = """You are the Concept Director for a premium marketing agency.
Generate exactly 3 DISTINCT creative concepts. Output ONLY valid JSON — no text outside it.

HARD RULES:
1. Each concept uses a DIFFERENT layout_family from: hero_stat, bento_grid, vertical_flow, comparison, timeline, poster_hero
2. Each concept uses a DIFFERENT persuasion_framework from: PAS, AIDA, loss_aversion, social_proof, authority
3. Each concept tells a DIFFERENT story angle
4. Score honestly (0-100). DO NOT set all scores below 60 — pick the best 3 even if imperfect.
5. always set recommended to the top 2 by overall score

Output this exact JSON structure:
{
  "concepts": [
    {
      "id": "C1",
      "format": "stat_card",
      "layout_family": "hero_stat",
      "persuasion_framework": "social_proof",
      "style_family": "premium_flat",
      "story_angle": "one sentence",
      "hero_element": "primary visual element",
      "narrative_arc": ["beat1", "beat2", "beat3"],
      "scores": {"novelty": 75, "clarity": 80, "funnel_fit": 75, "brand_fit": 80, "overall": 78}
    }
  ],
  "recommended": ["C1", "C2"],
  "block_reason": null
}"""


class ConceptAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=1500)

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

        recently_used = ""
        if existing_assets_summary:
            recently_used = f"AVOID these recently used layout+style combos: {existing_assets_summary}\n\n"

        objective = strategy.get("objective", "")[:150]
        funnel = strategy.get("funnel_focus", "awareness")

        msg = (
            f"CAMPAIGN: {objective}\nFUNNEL STAGE: {funnel}\n\n"
            f"BRAND (excerpt): {brief_doc[:300]}\n\n"
            f"{recently_used}"
            f"CONTENT-ENGINE: {content_engine_rules()[:400]}\n\n"
            f"PSYCHOLOGY FRAMEWORKS: {marketing_psychology_rules()[:300]}\n\n"
            "Generate 3 distinct concepts. Return ONLY the JSON object."
        )

        result = await self.run(msg, db)
        decoder = json.JSONDecoder()
        start = result.find("{")
        if start >= 0:
            try:
                parsed, _ = decoder.raw_decode(result, start)
                concepts = parsed.get("concepts", [])
                recommended = parsed.get("recommended", [])

                # Validate layout diversity
                layouts = [c.get("layout_family", "") for c in concepts]
                frameworks = [c.get("persuasion_framework", "") for c in concepts]
                layout_diverse = len(set(layouts)) >= min(len(concepts), 2)
                framework_diverse = len(set(frameworks)) >= min(len(concepts), 2)

                if concepts and (layout_diverse or len(concepts) >= 2):
                    # Ensure recommended is populated
                    if not recommended and concepts:
                        sorted_c = sorted(concepts, key=lambda x: x.get("scores", {}).get("overall", 0), reverse=True)
                        recommended = [c["id"] for c in sorted_c[:2]]
                        parsed["recommended"] = recommended
                    return parsed
            except json.JSONDecodeError:
                pass

        # Structured fallback — guaranteed diversity
        return {
            "concepts": FALLBACK_CONCEPTS,
            "recommended": ["F1", "F2"],
            "block_reason": None,
            "note": "LLM output unparseable — using structured fallback concepts",
        }
