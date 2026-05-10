import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.tools.memory_tools import get_brand_memory, get_project_memory

SYSTEM_PROMPT = """You are the Copy Agent for Sovereign. You write human Saudi Gulf marketing copy in Arabic and English.

CRITICAL:
- Call get_project_memory AND get_brand_memory before writing anything.
- Read approved_examples and write in that exact register.
- Read rejected_examples and avoid those patterns.
- Read constraints.excluded_topics and never mention them.
- Use ONLY facts from project memory. Never invent product features, categories, or claims.

WRITING RULES:
- Arabic must sound like a Saudi saying it naturally.
- Never translate word-for-word from English.
- Never sound corporate, robotic, or AI-generated.
- Use Gulf Saudi vocabulary naturally: خل، شوف، وش، يبيلك، الحين، يلا، جرّب، تمام.
- Avoid banned generic CTAs like "اضغط هنا".
- CTAs must come from the offers list and be specific to the offer.
- Keep Arabic warm, direct, and concise. Favor short sentences.
- If a claim is not certain, flag it instead of pretending it's verified.

CHANNEL RULES:
- Instagram: punchy opener, specific benefit, specific CTA, 5-10 hashtags
- LinkedIn: human, credible, 1-3 hashtags, no jargon
- X/Twitter: concise, sharp, no fluff
- Google Ads: tight, direct, within character limits

QUALITY CHECK:
- Does the Arabic sound like a WhatsApp message from a real Saudi?
- Does the English sound like a human wrote it, not a template?
- Would a Saudi reader find this cringe, formal, or translated? Fix it.

Output exact JSON:
{
  "copy_ar": "Arabic copy",
  "copy_en": "English copy",
  "cta_ar": "Arabic CTA",
  "cta_en": "English CTA",
  "hashtags_ar": ["hashtag1", "hashtag2"],
  "hashtags_en": ["#hashtag1"],
  "variants": [
    {"label": "A", "copy_ar": "...", "copy_en": "...", "cta_ar": "...", "cta_en": "..."},
    {"label": "B", "copy_ar": "...", "copy_en": "...", "cta_ar": "...", "cta_en": "..."}
  ],
  "claim_flags": []
}"""

TOOLS = [
    {
        "name": "get_project_memory",
        "description": "Get project memory (ICP, offers, tone, approved/rejected examples)",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "get_brand_memory",
        "description": "Get brand memory (voice, dos/don'ts)",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
]


class CopyAgent(BaseAgent):
    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=4096)
        self.tool_implementations = {
            "get_project_memory": self._get_project_memory,
            "get_brand_memory": self._get_brand_memory,
        }

    async def _get_project_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_project_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {
            "icp": mem.icp,
            "positioning": mem.positioning,
            "offers": mem.offers,
            "tone": mem.tone,
            "funnel_goals": mem.funnel_goals,
            "approved_examples": mem.approved_examples,
            "rejected_examples": mem.rejected_examples,
            "constraints": mem.constraints,
        }

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {"brand_voice": mem.brand_voice, "dos": mem.dos, "donts": mem.donts}

    async def generate_copy(
        self,
        db: AsyncSession,
        project_id: str,
        channel: str,
        asset_type: str,
        funnel_stage: str,
        language: str = "bilingual",
    ) -> dict:
        msg = (
            f"Generate {language} marketing copy for project_id={project_id}. "
            f"Channel: {channel}. Asset type: {asset_type}. Funnel stage: {funnel_stage}. "
            "First call get_project_memory, then get_brand_memory, then write the copy. "
            "Use approved_examples as style reference and avoid rejected_examples exactly. "
            "Return valid JSON with copy_ar, copy_en, cta_ar, cta_en, hashtags_ar, hashtags_en, variants, claim_flags."
        )
        result = await self.run(msg, db)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        return {"error": "could not parse copy JSON", "raw": result}
