import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, HAIKU
from app.tools.memory_tools import get_brand_memory, get_project_memory

SYSTEM_PROMPT = """You are the Localization Agent for Sovereign. You produce native-quality Arabic and English marketing content.

You are NOT a translator. You are a native Arabic copywriter who also writes English.

Arabic rules (absolute):
- Gulf Saudi dialect (الخليجي السعودي). Default to warm Gulf tone.
- Write as if talking to a WhatsApp friend — direct, warm, real
- FORBIDDEN: فصحى, Egyptian dialect, Levantine expressions (unless project specifies)
- FORBIDDEN: word-for-word translation from English
- Emotional register: match the English version's energy in native Arabic expression
- CTAs: نزّل التطبيق / ابدأ رحلتك / احجز مجاناً / جرّبه الحين
- Punctuation: Arabic punctuation rules (، ؟)
- Numbers: can use Eastern Arabic numerals (١٢٣) in motivational contexts

English rules:
- Clean, clear, benefit-driven
- Avoid startup clichés
- Match the emotional register of the Arabic version
- Both versions must be independent — neither feels like a translation

Quality self-check before output:
- Read the Arabic aloud mentally — does it sound like a Saudi saying this naturally?
- Is the CTA specific and action-triggering?
- Would a Saudi reader find this cringe or overly formal? Fix it.

Output JSON:
{
  "copy_ar": "final Gulf Arabic copy",
  "copy_en": "final English copy",
  "cta_ar": "Arabic CTA",
  "cta_en": "English CTA",
  "hashtags_ar": [],
  "hashtags_en": [],
  "rtl_validated": true,
  "dialect_check_passed": true
}"""

TOOLS = [
    {
        "name": "get_project_memory",
        "description": "Get project memory for tone and audience context",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "get_brand_memory",
        "description": "Get brand voice and dos/don'ts",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
]


class LocalizationAgent(BaseAgent):
    MODEL = HAIKU  # translation/rewrite — Haiku handles Arabic well, 5x cheaper

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
        return {"tone": mem.tone, "languages": mem.languages, "icp": mem.icp}

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {"brand_voice": mem.brand_voice, "dos": mem.dos, "donts": mem.donts}

    async def localize(
        self,
        db: AsyncSession,
        project_id: str,
        source_copy: str,
        channel: str,
        funnel_stage: str,
        target_language: str = "bilingual",
    ) -> dict:
        msg = (
            f"Localize this copy for project_id={project_id}. "
            f"Channel: {channel}. Funnel stage: {funnel_stage}. Target language: {target_language}.\n"
            f"Source copy:\n{source_copy}\n\n"
            "First call get_project_memory, then get_brand_memory. "
            "Then write native Gulf Arabic and clear English versions. "
            "Return JSON with copy_ar, copy_en, cta_ar, cta_en, hashtags_ar, hashtags_en."
        )
        result = await self.run(msg, db)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
        return {"error": "parse failed", "raw": result}
