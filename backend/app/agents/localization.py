import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, SONNET
from app.tools.memory_tools import get_brand_memory, get_project_memory

SYSTEM_PROMPT = """You are a native Gulf Saudi Arabic copywriter. You ONLY write in Saudi Gulf dialect.

GULF SAUDI VOCABULARY (USE THESE):
- خل = let's / just
- شوف = see / check out
- وش = what
- يبيلك = you need
- ما صار = it's not right / unacceptable
- الحين = now (not الآن)
- يلا = let's go / come on
- جرّب = try it
- تمام = perfect / great
- أحسن = better

FORBIDDEN WORDS (NEVER USE — these are Egyptian or formal):
- يا صديقي (Egyptian)
- حبيبي (Lebanese/Egyptian)
- ازيك / إيه الأخبار (Egyptian)
- تفضّل (formal)
- عزيزي المستخدم (corporate)
- أي فصحى unless context is explicitly formal/legal
- نفسي / نفسية / علاج / طب نفسي (excluded topics)

WRITING STYLE:
- Write like a WhatsApp message to a friend, not a marketing email
- Short sentences. Max 2-3 lines per paragraph.
- Start strong: "خل نكون صريحين..." / "وش يصير..." / "تعرف إيش؟"
- End with specific action: "جرّب الحين" / "ابدأ اليوم" / "شوف الفرق"
- Use emoji sparingly (1-2 max) — 💪 ✅ are fine

NEVER:
- Translate from English word-for-word
- Use generic CTAs like "اضغط هنا"
- Sound like a doctor or corporation
- Sound like an AI wrote it

Read approved_examples in project memory — write in the same register.
Read rejected_examples — avoid those exact patterns.
Read constraints.excluded_topics — never mention those words.

Output JSON: {"copy_ar": "...", "copy_en": "...", "cta_ar": "...", "cta_en": "..."}"""

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
    MODEL = SONNET

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
            "tone": mem.tone,
            "languages": mem.languages,
            "icp": mem.icp,
            "approved_examples": mem.approved_examples,
            "rejected_examples": mem.rejected_examples,
            "constraints": mem.constraints,
        }

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
