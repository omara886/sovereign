"""
Full Therapia pipeline:
Strategy → save plan → Copy → Localization → Design → QA → Approval notification
"""
import asyncio
import json
from datetime import date
from sqlalchemy import select

from app.database import SessionLocal
from app.models.project import Project
from app.models.weekly_plan import WeeklyPlan
from app.models.asset import Asset
from app.agents.strategy import StrategyAgent
from app.agents.copy import CopyAgent
from app.agents.localization import LocalizationAgent
from app.agents.design import DesignAgent
from app.agents.qa import QAAgent
from app.agents.approval_agent import ApprovalAgent


async def run():
    async with SessionLocal() as db:
        project = (await db.execute(
            select(Project).where(Project.slug == "therapia")
        )).scalar_one()
        project_id = str(project.id)
        print(f"Project: {project.name} ({project_id})\n")

        # ── 1. Strategy ──────────────────────────────────────────────
        print("1/6  Strategy Agent...")
        strategy = StrategyAgent()
        plan_data = await strategy.create_plan(db, project_id, date.today())

        plan = WeeklyPlan(
            project_id=project.id,
            week_start=date.today(),
            objective=plan_data.get("objective", ""),
            funnel_focus=plan_data.get("funnel_focus", "awareness"),
            tactics=plan_data.get("tactics", []),
            total_budget_estimate=plan_data.get("total_budget_estimate", 0),
            rationale=plan_data.get("rationale", ""),
            risk_flags=plan_data.get("risk_flags", []),
            status="approved",  # auto-approve for this test run
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        print(f"     ✓ Plan saved — {len(plan.tactics)} tactics\n")

        # ── 2-5. Copy → Localize → Design → QA per tactic ───────────
        copy_agent = CopyAgent()
        local_agent = LocalizationAgent()
        design_agent = DesignAgent()
        qa_agent = QAAgent()
        passed_assets = []

        tactics = plan.tactics[:2]  # first 2 tactics for speed
        for i, tactic in enumerate(tactics):
            channel = tactic.get("channel", "instagram")
            asset_type = tactic.get("asset_type", "post")
            print(f"2/6  Copy Agent — tactic {i+1}: {channel}/{asset_type}...")
            copy_data = await copy_agent.generate_copy(
                db, project_id, channel, asset_type,
                tactic.get("funnel_stage", "awareness"), "bilingual"
            )

            print(f"3/6  Localization Agent...")
            local_data = await local_agent.localize(
                db, project_id,
                copy_data.get("copy_en", copy_data.get("copy_ar", "")),
                channel, tactic.get("funnel_stage", "awareness"), "bilingual"
            )

            copy_ar = local_data.get("copy_ar") or copy_data.get("copy_ar", "")
            copy_en = local_data.get("copy_en") or copy_data.get("copy_en", "")
            cta_ar  = local_data.get("cta_ar")  or copy_data.get("cta_ar", "")
            cta_en  = local_data.get("cta_en")  or copy_data.get("cta_en", "")

            # Save asset record
            asset = Asset(
                project_id=project.id,
                weekly_plan_id=plan.id,
                type=asset_type,
                channel=channel,
                language="bilingual",
                copy_ar=copy_ar,
                copy_en=copy_en,
                status="qa_pending",
            )
            db.add(asset)
            await db.commit()
            await db.refresh(asset)

            print(f"4/6  Design Agent...")
            design_data = await design_agent.generate_design(
                db, project_id, str(asset.id),
                channel, copy_ar, copy_en, cta_ar, cta_en
            )
            asset.design_url = design_data.get("design_url")
            asset.design_thumbnail_url = design_data.get("thumbnail_url")
            await db.commit()

            print(f"5/6  QA Agent...")
            qa_result = await qa_agent.check_asset(
                db, project_id, copy_ar, copy_en, cta_ar, cta_en,
                channel, copy_data.get("claim_flags", [])
            )
            asset.qa_score = qa_result.get("qa_score", 0)
            asset.qa_passed = qa_result.get("qa_passed", False)
            asset.qa_notes = qa_result.get("checks", [])
            asset.status = "approval_pending" if asset.qa_passed else "qa_failed"
            await db.commit()

            score = qa_result.get("qa_score", 0)
            passed = qa_result.get("qa_passed", False)
            print(f"     QA score: {score}/100 — {'✓ PASS' if passed else '✗ FAIL'}")
            if passed:
                passed_assets.append(asset)
            print()

        # ── 6. Approval notifications ─────────────────────────────────
        if passed_assets:
            print(f"6/6  Approval Agent — notifying Omar ({len(passed_assets)} assets)...")
            approval_agent = ApprovalAgent()
            result = await approval_agent.notify_pending_assets(
                db, project_id, "Therapia", passed_assets
            )
            print(f"     Email sent: {result.get('email_sent')}")
            print(f"     Telegram sent: {result.get('telegram_sent')}")
            print(f"     Approval IDs: {result.get('approval_ids')}")
        else:
            print("6/6  No assets passed QA — check qa_notes above")

        print("\n✅ Pipeline complete.")
        print(f"   Check your email: oalomran443@gmail.com")
        print(f"   Or visit: http://localhost:3000/inbox")


asyncio.run(run())
