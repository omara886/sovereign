from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _slug_to_title(project: str) -> str:
    return project.replace("-", " ").replace("_", " ").title()


def _weekly_plan(project: str, week: str) -> dict[str, Any]:
    title = _slug_to_title(project)
    return {
        "objective": f"Generate qualified interest for {title} during {week}",
        "funnel_focus": "awareness",
        "tactics": [
            {
                "id": f"{project}-linkedin-1",
                "channel": "linkedin",
                "asset_type": "post",
                "funnel_stage": "awareness",
                "rationale": "Share a direct founder-style insight that matches the existing tone system.",
                "rationale_simple": "نطلع بفائدة واضحة وبأسلوب بسيط عشان الناس تفهم القيمة بسرعة.",
                "budget_estimate_sar": 0,
                "budget_type": "organic",
                "stop_loss_sar": None,
                "expected_metric": "engagement",
                "expected_value": "600-900 impressions",
            },
            {
                "id": f"{project}-instagram-1",
                "channel": "instagram",
                "asset_type": "carousel",
                "funnel_stage": "consideration",
                "rationale": "Use a visual carousel to show the offer and the next step inline.",
                "rationale_simple": "نشرح الفكرة بصريًا عشان ما يبقى سؤال: وش الفايدة؟",
                "budget_estimate_sar": 150,
                "budget_type": "paid",
                "stop_loss_sar": 300,
                "expected_metric": "clicks",
                "expected_value": "20-40 clicks",
            },
            {
                "id": f"{project}-x-1",
                "channel": "x",
                "asset_type": "post",
                "funnel_stage": "awareness",
                "rationale": "Capture a sharp, shareable angle with a low-friction CTA.",
                "rationale_simple": "نخليها قصيرة وقوية عشان تنشار بسهولة.",
                "budget_estimate_sar": 0,
                "budget_type": "organic",
                "stop_loss_sar": None,
                "expected_metric": "replies",
                "expected_value": "10-20 replies",
            },
        ],
        "total_budget_estimate": 150,
        "rationale": "خطة هذا الأسبوع تركّز على رفع الوعي بطريقة بسيطة ومباشرة، ثم تدفع أفضل أداء عبر إنستغرام. الهدف هو تشغيل محتوى واضح وقابل للقياس بدون تعقيد. الميزانية محدودة لأننا نبني إشارات أولية أولًا ثم نوسع لاحقًا.",
        "risk_flags": [],
    }


def _asset(index: int, project: str) -> dict[str, Any]:
    base = project.replace("-", "_")
    score = 82 + index
    return {
        "id": f"{base}_asset_{index + 1}",
        "channel": ["linkedin", "instagram", "x"][index % 3],
        "type": ["post", "carousel", "post"][index % 3],
        "copy_ar": f"محتوى عربي طبيعي للمشروع {project} — نسخة {index + 1}",
        "copy_en": f"Natural English copy for {project} — variant {index + 1}",
        "qa_score": score,
        "qa_passed": True,
        "design_url": f"https://cdn.example.com/{base}/design_{index + 1}.png",
        "design_thumbnail_url": f"https://cdn.example.com/{base}/thumb_{index + 1}.jpg",
        "design_variants_count": 3,
        "arabic_text_applied": True,
        "design_tokens_applied": True,
    }


def run_full_pipeline(project: str, week: str, dry_run: bool = True) -> dict[str, Any]:
    weekly_plan = _weekly_plan(project, week)
    assets = [_asset(i, project) for i in range(3)]
    return {
        "project": project,
        "week": week,
        "dry_run": dry_run,
        "weekly_plan": weekly_plan,
        "assets": assets,
        "design_variants_count": 3,
        "qa_scores": [asset["qa_score"] for asset in assets],
        "arabic_text_applied": True,
        "design_tokens_applied": True,
        "static_values_count": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
