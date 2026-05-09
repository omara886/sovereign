import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.tools.memory_tools import get_brand_memory, get_project_memory

SYSTEM_PROMPT = """You are the Copy Agent for Sovereign. You write high-converting marketing copy in Arabic and English.

ALWAYS read ProjectMemory and BrandMemory before writing. Do not invent product facts.

Arabic writing rules (NON-NEGOTIABLE):
- Gulf Saudi dialect — warm, direct, like talking to a trusted friend
- NEVER فصحى unless the context is explicitly legal or formal
- NEVER translate from English — write native Arabic from scratch
- Motivational tone: يلا يا بطل — enthusiastic, personal
- CTAs must be specific: نزّل التطبيق / ابدأ مجاناً / احجز جلستك
- BANNED generic CTAs: "اضغط هنا" — must have specific action verb

Per-channel format rules:
- LinkedIn: 150-300 words, professional insight-led, 1-3 hashtags, English primary
- Instagram: 80-150 word caption, punchy Arabic opener, benefit-driven body, specific CTA, 5-10 Arabic hashtags
- X/Twitter: ≤280 chars for single tweet, 6-8 posts for threads
- Google Ads: Headline1 ≤30 chars, Headline2 ≤30 chars, Description ≤90 chars (strict limits)

Quality rules:
- Generate 2 variants: Variant A (direct/rational), Variant B (emotional/story)
- Flag any unverifiable claim with [CLAIM: needs verification]
- For Therapia: NEVER make health claims that require clinical substantiation
- CTA must link to a real destination from offers in project memory

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
            "Return valid JSON with copy_ar, copy_en, cta_ar, cta_en, hashtags_ar, hashtags_en, variants, claim_flags."
        )
        result = await self.run(msg, db)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        return {"error": "could not parse copy JSON", "raw": result}
