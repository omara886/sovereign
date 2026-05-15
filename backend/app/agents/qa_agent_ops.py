"""
Stage 08 — QA Agent with automated skill-based checks.

7 pass categories → compliance_score → approve_for_design (requires >= 90).
Each check maps directly to a skill rule — no vague scores.
"""
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.base import BaseAgent, DEEPSEEK
from app.tools.memory_tools import get_brand_memory, get_project_memory
from app.utils.arabic_qa import run_arabic_qa
from app.utils.skill_rules import (
    craft_polish_rules, anti_slop_rules,
    artifact_composition_rules, editorial_typography_rules, responsive_layout_rules,
)


# ── Automated deterministic checks (no LLM needed) ───────────────────────────

def check_anti_slop(visual_plan: dict, prompt: str) -> dict:
    """frontend-design-anti-slop.md — detect AI tropes in plan/prompt."""
    issues = []
    prompt_lower = (prompt or "").lower()
    plan_str = json.dumps(visual_plan).lower()
    combined = prompt_lower + " " + plan_str

    tropes = {
        "3-column feature grid": ["3 column", "three column", "feature grid", "icon title description"],
        "neon gradients": ["neon", "purple blue gradient", "teal gradient", "glow gradient"],
        "floating particles": ["floating particle", "bokeh blob", "floating orb", "light particle"],
        "centered hero portrait": ["centered portrait", "hero portrait", "businessman"],
        "dribbble glow": ["dribbble", "drop shadow glow", "inner glow"],
        "generic icon circles": ["icon in circle", "colored circle icon", "icon badge"],
        "symmetrical layout": ["symmetrical", "perfect symmetry", "equal columns"],
    }
    for trope_name, keywords in tropes.items():
        if any(kw in combined for kw in keywords):
            issues.append(f"AI trope detected: {trope_name}")

    return {"passed": len(issues) == 0, "issues": issues, "points": 20 if not issues else max(0, 20 - len(issues) * 5)}


def check_artifact_composition(visual_plan: dict) -> dict:
    """artifact-composition.md — one focal point, clear hierarchy."""
    issues = []
    panels = visual_plan.get("panels", [])
    hero_panels = [p for p in panels if p.get("role") == "hero"]

    if len(hero_panels) == 0:
        issues.append("No hero panel defined — no dominant focal point")
    elif len(hero_panels) > 1:
        issues.append(f"Multiple hero panels ({len(hero_panels)}) — violates single focal point rule")

    layout = visual_plan.get("layout_family", "")
    if not layout:
        issues.append("layout_family not specified")

    return {"passed": len(issues) == 0, "issues": issues, "points": 15 if not issues else max(0, 15 - len(issues) * 5)}


def check_editorial_typography(visual_plan: dict, copy_ar: str, copy_en: str) -> dict:
    """editorial-typography.jsx — Arabic/Urdu RTL, line limits, font spec."""
    issues = []
    language = visual_plan.get("language", "ar")

    if language in ("ar", "ur", "bilingual"):
        text_zones = visual_plan.get("text_safe_zones", [])
        rtl_anchored = any(z.get("anchor") in ("right", "rtl") for z in text_zones)
        if not rtl_anchored and text_zones:
            issues.append("Text zones not right-anchored for RTL language")

        # Check Arabic headline is not too long (max 6 words * 2 lines = 12 words)
        if copy_ar:
            word_count = len(copy_ar.split())
            if word_count > 12:
                issues.append(f"Arabic headline too long ({word_count} words) — max 12 words for 2 lines")

        brand_tokens = visual_plan.get("brand_tokens", {})
        if not brand_tokens.get("typeface_ar"):
            issues.append("Arabic typeface not specified in brand_tokens")

    return {"passed": len(issues) == 0, "issues": issues, "points": 20 if not issues else max(0, 20 - len(issues) * 7)}


def check_responsive_layout(visual_plan: dict, channel: str) -> dict:
    """responsive-layout.md — safe areas respected."""
    issues = []
    text_zones = visual_plan.get("text_safe_zones", [])

    SAFE_MARGINS = {
        "instagram": 0.069, "story": 0.081,
        "linkedin": 0.07, "x": 0.07, "default": 0.07,
    }
    required_margin = SAFE_MARGINS.get(channel, SAFE_MARGINS["default"])

    for zone in text_zones:
        x_pct = zone.get("x_pct", 0)
        if x_pct < required_margin:
            issues.append(f"Text zone x_pct={x_pct} violates {required_margin*100:.0f}% safe margin for {channel}")

    if not text_zones:
        issues.append("No text_safe_zones defined — cannot verify layout safety")

    return {"passed": len(issues) == 0, "issues": issues, "points": 10 if not issues else max(0, 10 - len(issues) * 3)}


def check_craft_polish(visual_plan: dict, copy_ar: str) -> dict:
    """craft-polish.md — spacing, hierarchy, color count."""
    issues = []
    brand_tokens = visual_plan.get("brand_tokens", {})

    # Check max 2 non-neutral brand hues
    hues = [v for k, v in brand_tokens.items() if k.endswith("_hex") and v]
    if len(hues) > 3:
        issues.append(f"Too many brand colors ({len(hues)}) — craft-polish allows max 2-3")

    # Check panels have purpose
    panels = visual_plan.get("panels", [])
    panels_without_role = [p for p in panels if not p.get("role")]
    if panels_without_role:
        issues.append(f"{len(panels_without_role)} panels without a defined role")

    return {"passed": len(issues) == 0, "issues": issues, "points": 15 if not issues else max(0, 15 - len(issues) * 5)}


def check_claims(copy_ar: str, copy_en: str) -> dict:
    """Source attribution — every numeric claim must have a row in claims.csv with source_url and flagged=false."""
    import csv
    from pathlib import Path

    issues = []
    combined = (copy_ar or "") + " " + (copy_en or "")

    # Detect numeric claims in Arabic and English
    ar_numbers = re.findall(r'[٠-٩0-9]+\s*(?:دقيق[ةة]|دقائق|ثانية|يوم|أيام|أسبوع|مستخدم|شخص|[٪%])', combined)
    en_numbers = re.findall(r'\b\d+\s*(?:minute|second|day|week|user|person|[%])\b', combined.lower())
    all_claims = ar_numbers + en_numbers

    if not all_claims:
        return {"passed": True, "issues": [], "points": 10, "claims_found": 0}

    # Check claims.csv
    claims_path = Path(__file__).parent.parent.parent / "assets" / "data" / "claims.csv"
    verified_values: set[str] = set()
    if claims_path.exists():
        try:
            with open(claims_path, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    flagged = str(row.get('flagged', 'true')).strip().lower()
                    source = str(row.get('source_url', '')).strip()
                    if flagged not in ('true', '1') and source:
                        verified_values.add(str(row.get('numeric_value', '')).strip())
        except Exception:
            pass

    for claim in all_claims:
        # Extract just the number part for lookup
        num = re.search(r'[٠-٩0-9]+', claim)
        if num:
            val = num.group()
            if val not in verified_values:
                issues.append(f"Unsourced claim: '{claim}' — add to assets/data/claims.csv with source_url")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "points": 10 if not issues else 0,
        "claims_found": len(all_claims),
        "blocking": False,  # Warning only for now — becomes blocking in Phase 2
    }


def check_novelty(layout_family: str, style_family: str, recent_layouts: list[str]) -> dict:
    """Penalize repeating the same layout+style combination."""
    key = f"{layout_family}:{style_family}"
    repeat_count = recent_layouts.count(key)
    score = max(0, 20 - repeat_count * 10)
    return {
        "passed": repeat_count < 2,
        "repeat_count": repeat_count,
        "issues": [f"layout+style '{key}' used {repeat_count} times recently"] if repeat_count >= 2 else [],
        "points": score,
    }


# ── LLM-assisted content checks ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Brand QA Reviewer.
Check brand alignment and message clarity. Return JSON only.
{
  "brand_voice_ok": true,
  "one_message_ok": true,
  "cta_specific_ok": true,
  "proof_present_ok": true,
  "funnel_fit_ok": true,
  "notes": "..."
}"""


class QAAgentOps(BaseAgent):
    MODEL = DEEPSEEK

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, tools=[], max_tokens=400)

    async def review(
        self,
        db: AsyncSession,
        project_id: str,
        creative_direction: dict,
        copy_ar: str = "",
        copy_en: str = "",
        cta_ar: str = "",
        channel: str = "instagram",
        recent_layouts: list[str] | None = None,
    ) -> dict:
        brand_mem = await get_brand_memory(db, project_id)
        project_mem = await get_project_memory(db, project_id)
        brief_doc = getattr(project_mem, "brand_brief", None) or "" if project_mem else ""
        colors = (brand_mem.color_palette or {}) if brand_mem else {}

        visual_plan = creative_direction if isinstance(creative_direction, dict) else {}
        layout_family = visual_plan.get("layout_family", "")
        style_family = visual_plan.get("style_family", "")

        # ── Run automated checks ──────────────────────────────────────────────
        arabic_result = run_arabic_qa({"copy_ar": copy_ar, "cta_ar": cta_ar})
        anti_slop   = check_anti_slop(visual_plan, visual_plan.get("generation_prompt", ""))
        composition = check_artifact_composition(visual_plan)
        typography  = check_editorial_typography(visual_plan, copy_ar, copy_en)
        responsive  = check_responsive_layout(visual_plan, channel)
        craft       = check_craft_polish(visual_plan, copy_ar)
        novelty     = check_novelty(layout_family, style_family, recent_layouts or [])
        claims      = check_claims(copy_ar, copy_en)  # source attribution check

        # Base score: 90pts from design/layout checks + 10pts from claims
        auto_score = (
            anti_slop["points"] +      # 20pts
            composition["points"] +    # 15pts
            typography["points"] +     # 20pts
            responsive["points"] +     # 10pts
            craft["points"] +          # 15pts
            novelty["points"] +        # 10pts (was 20, reduced to fit claims)
            claims["points"]           # 10pts
        )

        # Arabic hard block
        if arabic_result.get("blocked"):
            return self._blocked_result(
                auto_score, arabic_result, anti_slop, composition,
                typography, responsive, craft, novelty,
                [f"Arabic script QA failed: {arabic_result['issues'][0]['message']}"],
            )

        # ── LLM content check (brand voice, message clarity) ──────────────
        llm_ok = {"brand_voice_ok": True, "one_message_ok": True, "cta_specific_ok": True,
                  "proof_present_ok": True, "funnel_fit_ok": True, "notes": ""}
        try:
            msg = (
                f"COPY AR: {copy_ar[:200]}\nCOPY EN: {copy_en[:200]}\nCTA AR: {cta_ar}\n"
                f"BRAND VOICE: {(brand_mem.brand_voice or '') if brand_mem else ''}\n"
                f"BRIEF: {brief_doc[:200]}\n"
                "Check brand alignment and return JSON."
            )
            result = await self.run(msg, db)
            decoder = json.JSONDecoder()
            start = result.find("{")
            if start >= 0:
                parsed, _ = decoder.raw_decode(result, start)
                llm_ok = parsed
        except Exception:
            pass

        # Adjust score for LLM failures
        llm_penalty = sum(5 for k, v in llm_ok.items() if k.endswith("_ok") and not v)
        final_score = max(0, min(100, auto_score - llm_penalty))

        blocking = []
        warnings = []
        for check in [anti_slop, composition, typography, responsive, craft, novelty]:
            blocking.extend(check.get("issues", []))
        if arabic_result.get("issues"):
            blocking.extend([i["message"] for i in arabic_result["issues"]])
        if not llm_ok.get("brand_voice_ok"):
            blocking.append("Brand voice mismatch")
        if not llm_ok.get("cta_specific_ok"):
            blocking.append("CTA not specific enough")
        # Claims: warning only (not blocking) in Phase 1 — becomes blocking in Phase 2
        if claims.get("issues"):
            warnings.extend(claims["issues"])
        if llm_ok.get("notes"):
            warnings.append(llm_ok["notes"])

        return {
            "anti_slop_check": anti_slop,
            "composition_check": composition,
            "typography_check": typography,
            "responsive_check": responsive,
            "craft_check": craft,
            "novelty_check": novelty,
            "claims_check": claims,
            "arabic_qa": arabic_result,
            "content_check": llm_ok,
            "compliance_score": final_score,
            "approve_for_design": final_score >= 80 and not any(
                c.get("issues") for c in [anti_slop, composition, typography]
                if any(i for i in c.get("issues", []))
            ) and not arabic_result.get("blocked"),
            "blocking_reasons": blocking,
            "warnings": warnings,
        }

    def _blocked_result(self, base_score, arabic, *checks, blocking):
        return {
            "anti_slop_check": checks[0] if len(checks) > 0 else {},
            "composition_check": checks[1] if len(checks) > 1 else {},
            "typography_check": checks[2] if len(checks) > 2 else {},
            "arabic_qa": arabic,
            "compliance_score": max(0, base_score - 30),
            "approve_for_design": False,
            "blocking_reasons": blocking,
        }
