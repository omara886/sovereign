import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.utils.arabic_qa import run_arabic_qa

SYSTEM_PROMPT = """You are the QA Agent for Sovereign marketing content. Score 0-100. Pass ≥70.

COPY QA (50pts):
- BRAND (15pts): tone matches Gulf Saudi brand voice; no Egyptian/formal Arabic
- ARABIC (15pts): Gulf Saudi dialect; reads natural; not translated EN word-for-word
- COPY (10pts): specific CTA from offers list; within channel character limits
- POLICY (10pts): no clinical treatment claims ("يعالج","مضمون","علمياً مثبت")
  NOTE: "track your health" / "monitor habits" = feature description NOT a claim. Do NOT penalize.
  Only penalize: "cures", "treats", "guaranteed results", "clinically proven".

DESIGN QA (50pts) — score the visual:
- CONCEPT (20pts): Is it a real scene/composition? Text-on-background → 0pts. Reject immediately.
  "No visual concept detected — requires actual scene or composition."
- ARABIC READABILITY (15pts): Is Arabic text large enough? Not crowded? Breathable spacing?
  If Arabic appears as boxes (⊠⊠⊠) → 0pts, required_fix: "Arabic font rendering failed"
- PREMIUM (15pts): Does it look like SAR 500/month studio or SAR 50 template?
  Would a Saudi professional share this proudly?
  Generic gradient → -10pts. Real scene with depth → full pts.

Call get_brand_memory then score both sections. Output JSON:
{"qa_score":85,"qa_passed":true,"checks":[{"check_name":"visual_concept","status":"pass","note":"Real scene detected","points_awarded":20}],"required_fixes":[]}

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
    MODEL = DEEPSEEK  # structured scoring — Haiku is fast + 5x cheaper

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
        # Arabic QA runs FIRST — CRITICAL issues block immediately, no LLM call needed
        arabic_result = run_arabic_qa({"copy_ar": copy_ar, "cta_ar": cta_ar})
        if arabic_result["blocked"]:
            return {
                "qa_score": 0,
                "qa_passed": False,
                "checks": [
                    {"check_name": "arabic_script_qa", "status": "fail",
                     "note": i["message"], "points_awarded": 0}
                    for i in arabic_result["issues"]
                ],
                "required_fixes": [i["message"] for i in arabic_result["issues"]],
                "arabic_qa": arabic_result,
            }

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
        brand_mem = await self._get_brand_memory(db, project_id)
        msg = (
            f"QA check. Channel: {channel}.\n"
            f"Arabic copy:\n{copy_ar}\n\nEnglish copy:\n{copy_en}\n"
            f"Arabic CTA: {cta_ar}\nEnglish CTA: {cta_en}\n"
            f"Claim flags: {claim_flags}\n\n"
            f"BRAND MEMORY:\n{json.dumps(brand_mem, default=str, ensure_ascii=False)}\n\n"
            "Score 4 QA categories. Return ONLY valid JSON with: qa_score (0-100), qa_passed (bool), checks array, required_fixes array."
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
    forbidden_en = ['leverage', 'empower', 'discover the power', 'journey to', 'revolutionize']
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
    # Only block generic question openers on CTAs — "Discover X" is fine as a CTA
    if cta_en.lower().startswith(('are you', 'do you', 'have you')):
        issues.append(f'Forbidden English CTA start: {cta_en.split()[0] if cta_en else "empty"}')
    return issues
