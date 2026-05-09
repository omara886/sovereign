from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.database import get_db
from app.models.project import Project

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Track running jobs in memory (good enough for single-user MVP)
_jobs: dict[str, dict] = {}


async def _run_plan(project_id: str, job_id: str):
    from app.database import SessionLocal
    from app.agents.strategy import StrategyAgent
    from app.models.weekly_plan import WeeklyPlan

    _jobs[job_id] = {"status": "running", "step": "Strategy Agent thinking...", "project_id": project_id}
    try:
        async with SessionLocal() as db:
            strategy = StrategyAgent()
            plan_data = await strategy.create_plan(db, project_id, date.today())
            plan = WeeklyPlan(
                project_id=project_id,
                week_start=date.today(),
                objective=plan_data.get("objective", ""),
                funnel_focus=plan_data.get("funnel_focus", "awareness"),
                tactics=plan_data.get("tactics", []),
                total_budget_estimate=plan_data.get("total_budget_estimate", 0),
                rationale=plan_data.get("rationale", ""),
                risk_flags=plan_data.get("risk_flags", []),
                status="pending_approval",
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            _jobs[job_id] = {
                "status": "done",
                "step": "Weekly plan ready for approval",
                "project_id": project_id,
                "plan_id": str(plan.id),
                "objective": plan.objective,
                "tactics_count": len(plan.tactics),
                "rationale": plan.rationale,
            }
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "step": str(exc), "project_id": project_id}


async def _run_full_pipeline(project_id: str, job_id: str):
    from app.database import SessionLocal
    from app.agents.strategy import StrategyAgent
    from app.agents.copy import CopyAgent
    from app.agents.localization import LocalizationAgent
    from app.agents.design import DesignAgent
    from app.agents.qa import QAAgent
    from app.agents.approval_agent import ApprovalAgent
    from app.models.weekly_plan import WeeklyPlan
    from app.models.asset import Asset
    from app.models.project import Project

    _jobs[job_id] = {"status": "running", "step": "Generating weekly plan...", "project_id": project_id}
    try:
        async with SessionLocal() as db:
            project = await db.get(Project, project_id)
            if not project:
                raise ValueError("Project not found")

            # Strategy
            strategy = StrategyAgent()
            plan_data = await strategy.create_plan(db, project_id, date.today())
            plan = WeeklyPlan(
                project_id=project_id,
                week_start=date.today(),
                objective=plan_data.get("objective", ""),
                funnel_focus=plan_data.get("funnel_focus", "awareness"),
                tactics=plan_data.get("tactics", []),
                total_budget_estimate=plan_data.get("total_budget_estimate", 0),
                rationale=plan_data.get("rationale", ""),
                risk_flags=plan_data.get("risk_flags", []),
                status="approved",
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

            tactics = (plan.tactics or [])[:2]
            copy_agent = CopyAgent()
            local_agent = LocalizationAgent()
            design_agent = DesignAgent()
            qa_agent = QAAgent()
            passed = []

            for i, tactic in enumerate(tactics):
                channel = tactic.get("channel", "instagram")
                asset_type = tactic.get("asset_type", "post")
                _jobs[job_id]["step"] = f"Writing copy for {channel} {asset_type} ({i+1}/{len(tactics)})..."

                copy_data = await copy_agent.generate_copy(
                    db, project_id, channel, asset_type,
                    tactic.get("funnel_stage", "awareness"), "bilingual"
                )
                _jobs[job_id]["step"] = f"Localizing content ({i+1}/{len(tactics)})..."
                local_data = await local_agent.localize(
                    db, project_id,
                    copy_data.get("copy_en", copy_data.get("copy_ar", "")),
                    channel, tactic.get("funnel_stage", "awareness"), "bilingual"
                )
                copy_ar = local_data.get("copy_ar") or copy_data.get("copy_ar", "")
                copy_en = local_data.get("copy_en") or copy_data.get("copy_en", "")
                cta_ar  = local_data.get("cta_ar")  or copy_data.get("cta_ar", "")
                cta_en  = local_data.get("cta_en")  or copy_data.get("cta_en", "")

                asset = Asset(
                    project_id=project_id,
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

                _jobs[job_id]["step"] = f"Generating design ({i+1}/{len(tactics)})..."
                design_data = await design_agent.generate_design(
                    db, project_id, str(asset.id), channel, copy_ar, copy_en, cta_ar, cta_en
                )
                asset.design_url = design_data.get("design_url")
                asset.design_thumbnail_url = design_data.get("thumbnail_url")
                await db.commit()

                _jobs[job_id]["step"] = f"Running QA ({i+1}/{len(tactics)})..."
                qa_result = await qa_agent.check_asset(
                    db, project_id, copy_ar, copy_en, cta_ar, cta_en,
                    channel, copy_data.get("claim_flags", [])
                )
                asset.qa_score = qa_result.get("qa_score", 0)
                asset.qa_passed = qa_result.get("qa_passed", False)
                asset.qa_notes = qa_result.get("checks", [])
                asset.status = "approval_pending" if asset.qa_passed else "qa_failed"
                await db.commit()
                if asset.qa_passed:
                    passed.append(asset)

            # Notifications
            if passed:
                _jobs[job_id]["step"] = "Sending approval notifications..."
                approval_agent = ApprovalAgent()
                result = await approval_agent.notify_pending_assets(
                    db, project_id, project.name, passed
                )
                _jobs[job_id] = {
                    "status": "done",
                    "step": f"{len(passed)} assets ready in Approval Inbox",
                    "project_id": project_id,
                    "plan_id": str(plan.id),
                    "assets_generated": len(tactics),
                    "assets_passed_qa": len(passed),
                    "email_sent": result.get("email_sent"),
                    "objective": plan.objective,
                }
            else:
                _jobs[job_id] = {
                    "status": "done",
                    "step": "Pipeline done — no assets passed QA",
                    "project_id": project_id,
                    "assets_passed_qa": 0,
                }
    except Exception as exc:
        _jobs[job_id] = {"status": "error", "step": str(exc), "project_id": project_id}


@router.post("/plan/{project_slug}")
async def trigger_plan(project_slug: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    import uuid
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_plan, str(project.id), job_id)
    return {"job_id": job_id, "status": "started", "message": f"Generating weekly plan for {project.name}"}


@router.post("/run/{project_slug}")
async def trigger_pipeline(project_slug: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    import uuid
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_full_pipeline, str(project.id), job_id)
    return {"job_id": job_id, "status": "started", "message": f"Full pipeline started for {project.name}"}


@router.get("/status/{job_id}")
async def job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
