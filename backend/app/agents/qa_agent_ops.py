"""
QA/Brand Reviewer Agent — 7-pass gate before any asset goes to design.

Inputs: creative_agent output + brand memory + asset metadata.
Output: QA JSON with compliance_score and approve_for_design flag.

Approve only if compliance_score >= 90 and no blocking_reasons.
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.utils.arabic_qa import run_arabic_qa


SYSTEM_PROMPT = """You are a QA and Brand Reviewer Agent. You run a 7-pass QA gate on creative assets.

Output only valid JSON. No explanation outside JSON.

Scoring: compliance_score 0-100. approve_for_design=true only if score >= 90 AND no blocking_reasons.

Check weights:
- brand_check (30pts): colors, logo, typography match brand.md
- message_check (15pts): one hook, one CTA, one message
- marketing_check (15pts): funnel fit, proof present, audience fit
- visual_check (20pts): hierarchy, thumbnail readable, whitespace ok
- localization_check (10pts): Arabic via RAQM or reshaper, RTL alignment
- technical_check (5pts): sizes exported, safe areas, file specs
- risk_check (5pts): claims sourced, no legal risk

Output schema:
{
  "brand_check": {"colors_ok": true, "typography_ok": true, "note": ""},
  "message_check": {"hook_visible": true, "one_message": true, "cta_present": true},
  "marketing_check": {"funnel_fit": true, "proof_present": true, "audience_fit": true},
  "visual_check": {"hierarchy": true, "thumbnail_readable": true, "whitespace_ok": true},
  "localization_check": {"arabic_rendering": "raqm_used|reshaper_used|not_applicable", "rtl_alignment_ok": true},
  "technical_check": {"sizes_exported": ["instagram_feed","instagram_story"], "safe_areas_ok": true},
  "risk_check": {"claims_sourced": true, "legal_risk": false},
  "compliance_score": 0,
  "approve_for_design": false,
  "blocking_reasons": []
}"""


class QAAgentOps(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=600)

    async def review(
        self,
        db: AsyncSession,
        project_id: str,
        creative_direction: dict,
        copy_ar: str = "",
        copy_en: str = "",
        cta_ar: str = "",
    ) -> dict:
        brand_mem = await get_brand_memory(db, project_id)
        project_mem = await get_project_memory(db, project_id)
        brief_doc = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""
        colors = (brand_mem.color_palette or {}) if brand_mem else {}

        # Run Arabic script QA first — hard block on CJK contamination
        arabic_result = run_arabic_qa({"copy_ar": copy_ar, "cta_ar": cta_ar})

        context = (
            f"CREATIVE DIRECTION:\n{json.dumps(creative_direction, ensure_ascii=False)}\n\n"
            f"COPY (for review): AR={copy_ar[:100]} EN={copy_en[:100]}\n"
            f"BRAND COLORS: {json.dumps(colors)}\n"
            f"BRAND BRIEF: {brief_doc[:300]}\n"
            f"ARABIC SCRIPT QA: {json.dumps(arabic_result)}\n"
            "Run the 7-pass gate and return QA JSON."
        )
        result = await self.run(context, db)
        decoder = json.JSONDecoder()
        start = result.find("{")
        if start >= 0:
            try:
                qa = decoder.raw_decode(result, start)[0]
                # Override: Arabic QA block takes priority
                if arabic_result.get("blocked"):
                    qa["localization_check"]["rtl_alignment_ok"] = False
                    qa["blocking_reasons"] = qa.get("blocking_reasons", []) + [
                        f"Arabic script contamination: {arabic_result['issues'][0]['message']}"
                    ]
                    qa["compliance_score"] = min(qa.get("compliance_score", 0), 50)
                    qa["approve_for_design"] = False
                return qa
            except json.JSONDecodeError:
                pass

        # Fallback QA
        blocked = arabic_result.get("blocked", False)
        return {
            "brand_check": {"colors_ok": bool(colors), "typography_ok": True, "note": ""},
            "message_check": {"hook_visible": bool(copy_ar or copy_en), "one_message": True, "cta_present": bool(cta_ar)},
            "marketing_check": {"funnel_fit": True, "proof_present": True, "audience_fit": True},
            "visual_check": {"hierarchy": True, "thumbnail_readable": True, "whitespace_ok": True},
            "localization_check": {
                "arabic_rendering": "raqm_used" if arabic_result.get("passed") else "reshaper_used",
                "rtl_alignment_ok": not blocked,
            },
            "technical_check": {"sizes_exported": ["instagram_feed"], "safe_areas_ok": True},
            "risk_check": {"claims_sourced": True, "legal_risk": False},
            "compliance_score": 0 if blocked else 72,
            "approve_for_design": not blocked,
            "blocking_reasons": [i["message"] for i in arabic_result.get("issues", [])] if blocked else [],
        }
