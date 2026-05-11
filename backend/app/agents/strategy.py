import json
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory, update_project_memory

SYSTEM_PROMPT = """You are the Strategy Agent for Sovereign.
You apply the content-engine skill content strategy rules to plan each week.

# content-engine content strategy rules:
- Build from source: what worked (approved_examples) + what failed (rejected_examples)
- Platform-native planning: Instagram tactics != LinkedIn tactics != X tactics
- One clear message per tactic. Not "build awareness and drive conversions" — pick one.
- Specificity: "Get 50 Instagram followers this week" not "grow social presence"
- Sequence matters: awareness before consideration before conversion

Your job: Create a precise weekly marketing plan for a specific project.

Read the project's memory carefully before making any recommendations. Do not invent facts about the project.

Plan creation rules:
1. Identify the highest-impact funnel stage for THIS week based on current metrics vs targets
2. Select 3-5 concrete, executable tactics — no vague recommendations
3. Always include at least one organic (SAR 0) tactic
4. For paid tactics: include stop-loss threshold (max spend before pausing)
5. Explain EVERY recommendation in 1-2 sentences a non-marketer can understand
6. Set specific, measurable expected outcomes per tactic

CRITICAL: Read the project's funnel_goals from ProjectMemory to determine the north star. Do not assume what the product does — use only what is in the memory.
- The primary_goal field on the project tells you the conversion objective
- The funnel_goals field shows current vs target metrics
- The constraints.excluded_topics field lists topics you must NEVER target
- The rejected_examples show tactics and content that failed — avoid them
- The approved_examples show what worked — build on those patterns

NEVER recommend tactics without "why this matters" explanation.
NEVER use marketing jargon without plain-language translation.
NEVER exceed budget_cap from project memory constraints.
NEVER create tactics that touch excluded_topics.

Output a JSON object matching this exact schema:
{
  "objective": "string — one sentence goal for the week",
  "funnel_focus": "awareness|consideration|conversion|retention",
  "tactics": [
    {
      "id": "unique string",
      "channel": "linkedin|instagram|x|google_ads|email",
      "asset_type": "post|carousel|story|ad_creative|ad_copy",
      "funnel_stage": "awareness|consideration|conversion|retention",
      "rationale": "technical rationale",
      "rationale_simple": "plain Arabic explanation (1-2 sentences)",
      "budget_estimate_sar": 0,
      "budget_type": "organic|paid",
      "stop_loss_sar": null,
      "expected_metric": "metric name",
      "expected_value": "e.g. 500-800 impressions"
    }
  ],
  "total_budget_estimate": 0,
  "rationale": "3-4 sentence Arabic summary for founder",
  "risk_flags": []
}"""

TOOLS = [
    {
        "name": "get_project_memory",
        "description": "Retrieve the project memory (ICP, positioning, offers, tone, funnel goals, constraints, performance learnings)",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "get_brand_memory",
        "description": "Retrieve brand memory (colors, fonts, voice, dos/don'ts)",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
]


class StrategyAgent(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=4096)
        self.tool_implementations = {
            "get_project_memory": self._get_project_memory,
            "get_brand_memory": self._get_brand_memory,
        }

    async def _get_project_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_project_memory(db, project_id)
        if not mem:
            return {"error": "no memory found"}
        return {
            "icp": mem.icp,
            "positioning": mem.positioning,
            "offers": mem.offers,
            "tone": mem.tone,
            "languages": mem.languages,
            "funnel_goals": mem.funnel_goals,
            "constraints": mem.constraints,
            "approved_examples": mem.approved_examples,
            "rejected_examples": mem.rejected_examples,
            "performance_learnings": mem.performance_learnings,
        }

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"error": "no brand memory found"}
        return {
            "color_palette": mem.color_palette,
            "typography": mem.typography,
            "visual_style": mem.visual_style,
            "brand_voice": mem.brand_voice,
            "dos": mem.dos,
            "donts": mem.donts,
            "is_provisional": mem.is_provisional,
        }

    async def create_plan(self, db: AsyncSession, project_id: str, week_start: date, founder_notes: str | None = None) -> dict:
        msg = f"Create weekly marketing plan for project_id={project_id}, week_start={week_start}."
        if founder_notes:
            msg += f"\nFounder notes: {founder_notes}"
        msg += "\nFirst call get_project_memory, then get_brand_memory, then output the plan JSON."
        result = await self.run(msg, db)
        # Extract JSON from response
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        return {"error": "could not parse plan JSON", "raw": result}
