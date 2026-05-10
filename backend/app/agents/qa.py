import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, HAIKU
from app.tools.memory_tools import get_brand_memory, get_project_memory

COPY_VALIDATION = """
COPY VALIDATION (blocks before approval inbox):
- copy_ar must be >= 30 characters (not empty or placeholder)
- copy_en must be >= 30 characters (not empty or placeholder)
- copy_ar must NOT contain: يا صديقي, حبيبي, ازيك, تفضّل, عزيزي المستخدم
- copy_ar must NOT contain any word from project constraints.excluded_topics
- copy_en must NOT contain: unlock, leverage, empower, discover the power, journey to, revolutionize
- copy_en must NOT start with: Are you, Do you, Have you, Discover, Unlock
- CTA must NOT be generic: "Click here", "Learn more", "اضغط هنا", "اعرف أكثر"
If ANY of these fail: qa_score = 0, qa_passed = false, required_fixes lists the specific violation.
"""

SYSTEM_PROMPT = """You are the QA Agent for Sovereign. Nothing reaches the founder's approval inbox without passing all your checks.

You are the last automated line of defense. A false pass is worse than a false fail. Be strict.

SCORING: 0-100. Pass threshold: ≥85. Warning zone: 70-84 (flag but pass). Fail: <70 (block, list required fixes).

BRAND QA (25 points):
- Tone matches BrandMemory voice profile: 10 pts
- No previously-rejected patterns in copy: 5 pts
- Typography follows brand rules (no banned fonts in design): 5 pts
- Visual style consistent with brand: 5 pts

COPY QA (25 points):
- No unverified claims (no [CLAIM:] flags unresolved): 10 pts
- CTA is specific and action-oriented (not "اضغط هنا"): 5 pts
- Character counts within channel limits: 5 pts
- No competitor mentions without approval: 5 pts

ARABIC QA (25 points):
- Copy is Gulf Saudi Arabic (not فصحى, not MSA): 10 pts
- RTL indicators present (Arabic characters flow correctly): 5 pts
- No awkward literal translations from English: 5 pts
- CTA is native Arabic (not translated): 5 pts

POLICY QA (25 points):
- Therapia: no health claims requiring clinical proof ("يعالج", "مضمون", "علمياً مثبت"): 10 pts
- No prohibited platform content (violence, adult): 10 pts
- Financial/product claims are accurate: 5 pts

""" + COPY_VALIDATION + """

Output exact JSON:
{
  "qa_score": 92.5,
  "qa_passed": true,
  "checks": [
    {"check_name": "tone_match", "status": "pass", "note": "Warm Gulf tone confirmed", "points_awarded": 10},
    ...
  ],
  "required_fixes": []
}

If qa_passed is false: required_fixes must be specific and actionable."""

TOOLS = [
    {
        "name": "get_brand_memory",
        "description": "Get brand voice, dos/don'ts, rejected styles",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
    {
        "name": "get_project_memory",
        "description": "Get project constraints and excluded topics",
        "input_schema": {
            "type": "object",
            "properties": {"project_id": {"type": "string"}},
            "required": ["project_id"],
        },
    },
]


class QAAgent(BaseAgent):
    MODEL = HAIKU  # structured scoring — Haiku is fast + 5x cheaper

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=TOOLS, max_tokens=2048)
        self.tool_implementations = {
            "get_brand_memory": self._get_brand_memory,
            "get_project_memory": self._get_project_memory,
        }

    async def _get_brand_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_brand_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {
            "brand_voice": mem.brand_voice,
            "dos": mem.dos,
            "donts": mem.donts,
            "rejected_styles": mem.rejected_styles,
            "is_provisional": mem.is_provisional,
        }

    async def _get_project_memory(self, db: AsyncSession, project_id: str) -> dict:
        mem = await get_project_memory(db, project_id)
        if not mem:
            return {"error": "not found"}
        return {
            "constraints": mem.constraints,
            "approved_examples": mem.approved_examples,
            "rejected_examples": mem.rejected_examples,
        }

    async def check_asset(
        self,
        db: AsyncSession,
        project_id: str,
        copy_ar: str,
        copy_en: str,
        cta_ar: str,
        cta_en: str,
        channel: str,
        claim_flags: list[str],
    ) -> dict:
        project_mem = await get_project_memory(db, project_id)
        excluded_topics = []
        if project_mem and isinstance(project_mem.constraints, dict):
            excluded_topics = project_mem.constraints.get('excluded_topics', []) or []
        issues = _validate_copy(copy_ar, copy_en, cta_ar, cta_en, excluded_topics)
        if issues:
            return {
                "qa_score": 0,
                "qa_passed": False,
                "checks": [{"check_name": "copy_validation", "status": "fail", "note": issue, "points_awarded": 0} for issue in issues],
                "required_fixes": issues,
            }
        msg = (
            f"QA check for project_id={project_id}. Channel: {channel}.\n"
            f"Arabic copy:\n{copy_ar}\n\n"
            f"English copy:\n{copy_en}\n\n"
            f"Arabic CTA: {cta_ar}\n"
            f"English CTA: {cta_en}\n"
            f"Claim flags from copy agent: {claim_flags}\n\n"
            "First call get_brand_memory, then score all 4 QA categories. "
            "Return JSON with qa_score, qa_passed, checks array, required_fixes array."
        )
        result = await self.run(msg, db)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(result[start:end])
            except json.JSONDecodeError:
                pass
        return {
            "qa_score": 0,
            "qa_passed": False,
            "checks": [],
            "required_fixes": ["QA agent failed to produce valid output — manual review required"],
        }


def _validate_copy(copy_ar: str, copy_en: str, cta_ar: str, cta_en: str, excluded_topics: list[str] | None = None) -> list[str]:
    issues: list[str] = []
    ar = (copy_ar or '').strip()
    en = (copy_en or '').strip()
    cta_ar = (cta_ar or '').strip()
    cta_en = (cta_en or '').strip()
    excluded = [topic.strip() for topic in (excluded_topics or []) if topic]

    if len(ar) < 30:
      issues.append('Arabic copy too short or empty')
    if len(en) < 30:
      issues.append('English copy too short or empty')

    forbidden_ar = ['يا صديقي', 'حبيبي', 'ازيك', 'تفضّل', 'عزيزي المستخدم']
    forbidden_en = ['unlock', 'leverage', 'empower', 'discover the power', 'journey to', 'revolutionize']
    for phrase in forbidden_ar:
        if phrase in ar:
            issues.append(f'Forbidden Arabic phrase: {phrase}')
    for phrase in forbidden_en:
        if phrase.lower() in en.lower():
            issues.append(f'Forbidden English phrase: {phrase}')
    for topic in excluded:
        if topic and (topic in ar or topic.lower() in en.lower()):
            issues.append(f'Excluded topic used: {topic}')

    generic_ctas = ['Click here', 'Learn more', 'اضغط هنا', 'اعرف أكثر']
    if any(cta.lower() == generic.lower() for generic in generic_ctas for cta in [cta_en, cta_ar]):
        issues.append('Generic CTA detected')
    if cta_en.lower().startswith(('are you', 'do you', 'have you', 'discover', 'unlock')):
        issues.append(f'Forbidden English CTA start: {cta_en.split()[0] if cta_en else "empty"}')
    return issues
