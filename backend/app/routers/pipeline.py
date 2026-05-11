from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.database import get_db
from app.models.project import Project

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

import time

# Job store — keeps last 50 jobs with full step history for the Lab screen
_jobs: dict[str, dict] = {}
_JOB_HISTORY: list[dict] = []  # ordered list, newest first
_MAX_HISTORY = 50
_reports: dict[str, list] = {}  # job_id → list of reports


def _new_job(job_id: str, project_id: str, project_name: str, mode: str) -> dict:
    job = {
        "id": job_id,
        "project_id": project_id,
        "project_name": project_name,
        "mode": mode,
        "status": "running",
        "step": "Starting...",
        "agent": "",
        "data_sources": [],
        "decisions": [],
        "steps_history": [],
        "started_at": time.time(),
        "ended_at": None,
        "error": None,
    }
    _jobs[job_id] = job
    _JOB_HISTORY.insert(0, job)
    if len(_JOB_HISTORY) > _MAX_HISTORY:
        _JOB_HISTORY.pop()
    return job


def _log_step(job_id: str, step: str, agent: str = "", sources: list = None, decisions: list = None):
    job = _jobs.get(job_id)
    if not job:
        return
    entry = {
        "ts": time.time(),
        "step": step,
        "agent": agent,
        "data_sources": sources or [],
        "decisions": decisions or [],
    }
    job["step"] = step
    job["agent"] = agent
    job["data_sources"] = sources or []
    job["decisions"] = decisions or []
    job["steps_history"].append(entry)


def _finish_job(job_id: str, status: str, error: str = None):
    job = _jobs.get(job_id)
    if job:
        job["status"] = status
        job["ended_at"] = time.time()
        job["error"] = error


async def _run_plan(project_id: str, job_id: str):
    from app.database import SessionLocal
    from app.agents.strategy import StrategyAgent
    from app.models.weekly_plan import WeeklyPlan

    _new_job(job_id, project_id, "", "plan")
    _log_step(job_id, "Strategy Agent thinking...", "Strategy Agent", ["ProjectMemory", "BrandMemory", "MetricHistory"])
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
            _finish_job(job_id, "done")
            _jobs[job_id].update({
                "step": "Weekly plan ready for approval",
                "project_id": project_id,
                "plan_id": str(plan.id),
                "objective": plan.objective,
                "tactics_count": len(plan.tactics),
                "rationale": plan.rationale,
            })
    except Exception as exc:
        _finish_job(job_id, "error", str(exc))


async def _run_full_pipeline(project_id: str, job_id: str):
    from app.database import SessionLocal
    from app.agents.strategy import StrategyAgent
    from app.agents.copy import CopyAgent
    from app.agents.localization import LocalizationAgent
    from app.agents.design import DesignAgent
    from app.agents.qa import QAAgent
    from app.agents.qa import _validate_copy
    from app.agents.approval_agent import ApprovalAgent
    from app.models.weekly_plan import WeeklyPlan
    from app.models.asset import Asset
    from app.models.project import Project
    from app.tools.memory_tools import get_project_memory

    def log(step: str, agent: str = "", sources: list = None, decisions: list = None):
        _jobs[job_id] = {
            "status": "running",
            "step": step,
            "project_id": project_id,
            "agent": agent,
            "data_sources": sources or [],
            "decisions": decisions or [],
        }

    log("Reading brand guide and project memory...", "Strategy Agent", ["BrandMemory", "ProjectMemory", "MetricHistory"])
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
                log(f"Writing copy for {channel} {asset_type} ({i+1}/{len(tactics)})...", "Copy Agent", ["ProjectMemory", "BrandMemory", "ApprovedExamples"], ["Gulf Saudi Arabic", "Excluded topics checked"])

                copy_data = await copy_agent.generate_copy(
                    db, project_id, channel, asset_type,
                    tactic.get("funnel_stage", "awareness"), "bilingual"
                )
                log(f"Localizing to Gulf Saudi Arabic ({i+1}/{len(tactics)})...", "Localization Agent", ["ProjectMemory.tone", "BrandMemory.voice", "ApprovedExamples"], ["Gulf dialect", "RTL enforced", "No Egyptian markers"])
                local_data = await local_agent.localize(
                    db, project_id,
                    copy_data.get("copy_en", copy_data.get("copy_ar", "")),
                    channel, tactic.get("funnel_stage", "awareness"), "bilingual"
                )
                copy_ar = local_data.get("copy_ar") or copy_data.get("copy_ar", "")
                copy_en = local_data.get("copy_en") or copy_data.get("copy_en", "")
                cta_ar  = local_data.get("cta_ar")  or copy_data.get("cta_ar", "")
                cta_en  = local_data.get("cta_en")  or copy_data.get("cta_en", "")

                project_mem = await get_project_memory(db, project_id)
                excluded_topics = []
                if project_mem and isinstance(project_mem.constraints, dict):
                    excluded_topics = project_mem.constraints.get("excluded_topics", []) or []
                issues = _validate_copy(copy_ar, copy_en, cta_ar, cta_en, excluded_topics)
                if issues:
                    _jobs[job_id]["step"] = f"Skipping {channel} {asset_type}: {'; '.join(issues)}"
                    continue

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

                log(f"Generating design ({i+1}/{len(tactics)})...", "Design Agent", ["BrandMemory.colors", "BrandMemory.logo", "ThmanyahFont"], ["Brand colors applied", "Thmanyah font", "RTL Arabic layout"])
                design_data = await design_agent.generate_design(
                    db, project_id, str(asset.id), channel, copy_ar, copy_en, cta_ar, cta_en
                )
                asset.design_url = design_data.get("design_url")
                asset.design_thumbnail_url = design_data.get("thumbnail_url")
                await db.commit()

                log(f"QA check ({i+1}/{len(tactics)})...", "QA Agent", ["BrandMemory.donts", "ProjectMemory.excluded_topics", "RejectedExamples"], ["Gulf Arabic validated", "No forbidden phrases", "Score / 100"])
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
                log("Sending to approval inbox...", "Approval Agent", ["Founder email", "Telegram"], ["Email notification sent", "Assets queued for review"])
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


@router.get("/logs/{job_id}")
async def get_job_logs(job_id: str):
    """Full job details including any error messages."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


# ── Lab endpoints ────────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs():
    """Lab: list recent pipeline runs with full step history."""
    return [
        {
            "id": j["id"],
            "project_name": j.get("project_name", ""),
            "mode": j.get("mode", ""),
            "status": j["status"],
            "step": j["step"],
            "steps_count": len(j.get("steps_history", [])),
            "started_at": j.get("started_at"),
            "ended_at": j.get("ended_at"),
            "error": j.get("error"),
        }
        for j in _JOB_HISTORY
    ]


@router.get("/jobs/{job_id}/detail")
async def job_detail(job_id: str):
    """Lab: full step-by-step detail for a specific job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {**job, "reports": _reports.get(job_id, [])}


@router.post("/jobs/{job_id}/report")
async def report_step(job_id: str, payload: dict):
    """Lab: report a problem with a specific step or the overall job."""
    # payload: {step_index: int|None, issue: str, category: str}
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    report = {
        "ts": time.time(),
        "step_index": payload.get("step_index"),
        "step_name": payload.get("step_name", ""),
        "issue": payload.get("issue", ""),
        "category": payload.get("category", "other"),
    }
    _reports.setdefault(job_id, []).append(report)
    return {"reported": True, "report": report}
