"""
Marketing Agent — decides WHAT to make and whether to make it at all.

Inputs: campaign_brief dict + brand memory from DB.
Output: decision JSON with asset_type, rationale, format, tone, sources check.

Rules:
- Returns "no_asset" if brief has unsourced numeric claims
- Maps funnel_stage to asset formats
- Prefers cheap formats (stat_card) over expensive (poster_hero) unless emotional aspiration required
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory


SYSTEM_PROMPT = """You are a Marketing Strategist Agent. You decide whether a creative asset should be made and in what format.

You output only valid JSON. No explanation outside the JSON.

Rules:
1. If campaign_brief contains any numeric claim (%, number, stat) without a source_url, return "decision":"no_asset" and list missing sources.
2. Map funnel_stage to formats: awareness → poster_hero or mascot_scene, consideration → infographic or carousel, conversion → stat_card or ui_mock.
3. Prefer stat_card over poster_hero unless emotional aspiration is clearly required.
4. If objective can be achieved without AI image generation, choose a cheaper format.

Output schema:
{
  "decision": "no_asset" | "asset_type",
  "asset_type": "stat_card|poster_hero|infographic|carousel|story|ui_mock|mascot_scene",
  "reason": "<one sentence>",
  "success_metric": "<primary KPI>",
  "missing_sources": ["claim_text if no source"],
  "must_have_proof": true|false,
  "tone": "playful|premium|clinical|warm|bold",
  "primary_audience_segment": "...",
  "channels": ["instagram|linkedin|x|story"],
  "estimated_complexity": "low|medium|high"
}"""


class MarketingAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=600)

    async def decide(
        self,
        db: AsyncSession,
        project_id: str,
        campaign_brief: dict,
    ) -> dict:
        brand_mem = await get_brand_memory(db, project_id)
        project_mem = await get_project_memory(db, project_id)
        brief_doc = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""

        context = (
            f"CAMPAIGN BRIEF:\n{json.dumps(campaign_brief, ensure_ascii=False)}\n\n"
            f"BRAND BRIEF (first 400 chars):\n{brief_doc[:400]}\n\n"
            f"BRAND VOICE: {brand_mem.brand_voice if brand_mem else 'not set'}\n"
            f"FUNNEL GOALS: {json.dumps(project_mem.funnel_goals if project_mem else {})}\n"
            "Return the decision JSON only."
        )
        result = await self.run(context, db)
        decoder = json.JSONDecoder()
        start = result.find("{")
        if start >= 0:
            try:
                parsed, _ = decoder.raw_decode(result, start)
                return parsed
            except json.JSONDecodeError:
                pass
        return {"decision": "no_asset", "reason": "Could not parse marketing-agent response", "raw": result[:200]}
