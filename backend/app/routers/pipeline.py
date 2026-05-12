import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timezone

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

    # Initialize job properly so steps_history is tracked and Lab shows real logs
    _new_job(job_id, project_id, "", "full")

    def log(step: str, agent: str = "", sources: list = None, decisions: list = None):
        _log_step(job_id, step, agent, sources, decisions)

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
                from sqlalchemy.orm.attributes import flag_modified
                new_variants = list(design_data.get("variants", []))
                mem_snap = design_data.get("memory_snapshot", {})
                _log_step(job_id, f"Saving design: {len(new_variants)} variants", "Design Agent")
                # Assign Python objects directly — asyncpg handles JSONB natively
                asset.design_url           = design_data.get("design_url")
                asset.design_thumbnail_url = design_data.get("thumbnail_url")
                asset.variants             = new_variants
                asset.design_prompt        = json.dumps({
                    "memory_snapshot": mem_snap,
                    "model_used": design_data.get("model_used", ""),
                    "fal_prompt": new_variants[0].get("fal_prompt", "") if new_variants else "",
                })
                asset.copy_bilingual = {"cta_ar": cta_ar, "cta_en": cta_en}
                # Force SQLAlchemy to mark JSONB columns as dirty
                flag_modified(asset, "variants")
                flag_modified(asset, "copy_bilingual")
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
                _log_step(job_id, f"{len(passed)} asset(s) sent to Approval Inbox", "Approval Agent",
                          decisions=[f"{len(passed)} passed QA", "Telegram notification sent"])
            else:
                _log_step(job_id, "Pipeline done — no assets passed QA", "QA Agent")

            _finish_job(job_id, "done")
            job = _jobs.get(job_id, {})
            job["project_name"] = project.name
            job["plan_id"] = str(plan.id)
            job["assets_generated"] = len(tactics)
            job["assets_passed_qa"] = len(passed)
            job["objective"] = plan.objective
            job["step"] = f"{len(passed)} asset(s) ready in Approval Inbox" if passed else "Pipeline done — no assets passed QA"
    except Exception as exc:
        _log_step(job_id, f"Error: {exc}", "System")
        _finish_job(job_id, "error", str(exc))


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
    # Pre-initialize with project name so Lab shows it immediately
    _new_job(job_id, str(project.id), project.name, "full")
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


# ── Lab control-room status ───────────────────────────────────────────────────

AGENT_SEQUENCE = [
    {"key": "strategy",   "name": "Strategy Agent",     "icon": "🧠"},
    {"key": "copy",       "name": "Copy Agent",          "icon": "✍️"},
    {"key": "localize",   "name": "Localization Agent",  "icon": "🌍"},
    {"key": "design",     "name": "Design Agent",        "icon": "🎨"},
    {"key": "qa",         "name": "QA Agent",            "icon": "✅"},
    {"key": "approval",   "name": "Approval Agent",      "icon": "📨"},
    {"key": "publish",    "name": "Publishing Agent",    "icon": "🚀"},
    {"key": "analytics",  "name": "Analytics Agent",     "icon": "📊"},
    {"key": "brand",      "name": "Brand Agent",         "icon": "🏷️"},
]

_AGENT_KEYWORDS = {
    "strategy":  ["strategy", "plan", "tactic"],
    "copy":      ["copy", "writing", "content"],
    "localize":  ["localiz", "arabic", "rtl", "gulf"],
    "design":    ["design", "fal", "image", "visual"],
    "qa":        ["qa", "quality", "check", "validat"],
    "approval":  ["approval", "inbox", "notif", "email", "telegram"],
    "publish":   ["publish", "schedul", "post"],
    "analytics": ["analytic", "metric", "insight"],
    "brand":     ["brand", "logo", "color", "font"],
}


def _infer_agent_key(step_text: str, agent_name: str) -> str:
    text = (step_text + " " + agent_name).lower()
    for key, keywords in _AGENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return key
    return ""


def _build_agent_statuses(job: dict | None) -> list[dict]:
    agents = []
    if not job:
        for a in AGENT_SEQUENCE:
            agents.append({**a, "status": "idle", "last_output": "", "time_taken": "", "error": None})
        return agents

    steps = job.get("steps_history", [])
    current_step = job.get("step", "")
    current_agent_key = _infer_agent_key(current_step, job.get("agent", ""))
    job_status = job.get("status", "running")

    for a in AGENT_SEQUENCE:
        key = a["key"]
        # Find this agent's steps
        agent_steps = [s for s in steps if _infer_agent_key(s.get("step", ""), s.get("agent", "")) == key]
        if agent_steps:
            last = agent_steps[-1]
            duration = ""
            if len(agent_steps) >= 2:
                duration = f"{round(agent_steps[-1]['ts'] - agent_steps[0]['ts'], 1)}s"
            status = "done"
            if job_status == "running" and key == current_agent_key:
                status = "running"
            agents.append({
                **a,
                "status": status,
                "last_output": last.get("step", ""),
                "time_taken": duration,
                "error": None,
            })
        elif key == current_agent_key and job_status == "running":
            agents.append({**a, "status": "running", "last_output": current_step, "time_taken": "", "error": None})
        elif job_status == "error" and key == current_agent_key:
            agents.append({**a, "status": "error", "last_output": current_step, "time_taken": "", "error": job.get("error")})
        else:
            agents.append({**a, "status": "idle", "last_output": "", "time_taken": "", "error": None})

    return agents


@router.get("/lineage/{asset_id}")
async def asset_lineage(asset_id: str, db: AsyncSession = Depends(get_db)):
    """Full lineage for one asset: strategy → copy → design → QA → approval → publish."""
    from app.models.asset import Asset
    from app.models.approval import Approval
    from app.models.publish_job import PublishJob
    from app.models.project import Project
    from uuid import UUID

    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(400, "invalid asset_id")

    asset = await db.get(Asset, asset_uuid)
    if not asset:
        raise HTTPException(404, "asset not found")

    project = await db.get(Project, asset.project_id)

    # Weekly plan + tactic that generated this asset
    plan = None
    tactic = None
    if asset.weekly_plan_id:
        from app.models.weekly_plan import WeeklyPlan
        plan = await db.get(WeeklyPlan, asset.weekly_plan_id)
        if plan and plan.tactics:
            # Match tactic by channel + asset type
            for t in plan.tactics:
                if t.get("channel") == asset.channel and t.get("asset_type") == asset.type:
                    tactic = t
                    break
            if not tactic and plan.tactics:
                tactic = plan.tactics[0]

    # Approval decision
    approval = (await db.execute(
        select(Approval).where(Approval.asset_id == asset_uuid).limit(1)
    )).scalar_one_or_none()

    # Publish job
    pub = (await db.execute(
        select(PublishJob).where(PublishJob.asset_id == asset_uuid).limit(1)
    )).scalar_one_or_none()

    return {
        "asset_id": str(asset.id),
        "project": project.name if project else "Unknown",
        "project_slug": project.slug if project else "",
        "channel": asset.channel,
        "type": asset.type,
        "language": asset.language,
        "status": asset.status,
        "lineage": [
            {
                "stage": "Strategy",
                "agent": "Strategy Agent",
                "output": plan.objective if plan else "No plan",
                "detail": f"Funnel: {plan.funnel_focus}" if plan else "",
                "status": "done" if plan else "missing",
            },
            {
                "stage": "Tactic",
                "agent": "Strategy Agent",
                "output": f"{asset.channel} {asset.type}" if tactic else f"{asset.channel} {asset.type}",
                "detail": tactic.get("rationale_simple", tactic.get("rationale", "")) if tactic else "Tactic from weekly plan",
                "status": "done" if tactic else "done",
            },
            {
                "stage": "Copy",
                "agent": "Copy Agent + Localization",
                "output": (asset.copy_ar or asset.copy_en or "")[:100],
                "detail": f"CTA: {asset.cta_ar or asset.cta_en or '—'}",
                "status": "done" if (asset.copy_ar or asset.copy_en) else "missing",
            },
            {
                "stage": "Design",
                "agent": "Design Agent (fal.ai)",
                "output": "Creative generated" if asset.design_url else "No creative",
                "detail": f"Thumbnail: {'✓' if asset.design_thumbnail_url else '✗'}",
                "status": "done" if asset.design_url else "failed",
            },
            {
                "stage": "QA",
                "agent": "QA Agent",
                "output": f"Score: {asset.qa_score}/100" if asset.qa_score is not None else "Not scored",
                "detail": "Passed" if asset.qa_passed else ("Failed" if asset.qa_score is not None else "Pending"),
                "status": "done" if asset.qa_passed else ("failed" if asset.qa_score is not None else "pending"),
            },
            {
                "stage": "Approval",
                "agent": "Founder Decision",
                "output": approval.decision if approval else "Pending",
                "detail": f"Rejected: {approval.reason}" if (approval and approval.decision == 'rejected') else "",
                "status": "done" if (approval and approval.decision == 'approved') else
                          "failed" if (approval and approval.decision == 'rejected') else "pending",
            },
            {
                "stage": "Published",
                "agent": "Publishing Agent",
                "output": f"Posted at {pub.published_at}" if (pub and pub.published_at) else
                          f"Scheduled: {pub.scheduled_at}" if pub else "Not scheduled",
                "detail": pub.platform_post_id or "",
                "status": "done" if (pub and pub.published_at) else
                          "running" if pub else "idle",
            },
        ],
    }


@router.post("/regenerate-design/{asset_id}")
async def regenerate_design(
    asset_id: str, background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate 2 campaign variants for an existing asset (runs in background)."""
    from uuid import UUID
    from app.models.asset import Asset as AssetModel
    try:
        a_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(400, "invalid asset_id")
    asset = await db.get(AssetModel, a_uuid)
    if not asset:
        raise HTTPException(404, "asset not found")

    async def _regen():
        from app.database import SessionLocal
        from app.agents.design import DesignAgent
        from sqlalchemy.orm.attributes import flag_modified as _flag
        async with SessionLocal() as session:
            a = await session.get(AssetModel, a_uuid)
            if not a:
                return
            agent = DesignAgent()
            cb = a.copy_bilingual if isinstance(a.copy_bilingual, dict) else {}
            design_data = await agent.generate_design(
                session, str(a.project_id), str(a.id), a.channel,
                a.copy_ar or '', a.copy_en or '',
                cb.get('cta_ar', ''), cb.get('cta_en', ''),
            )
            new_variants = list(design_data.get('variants', []))
            a.design_url           = design_data.get('design_url')
            a.design_thumbnail_url = design_data.get('thumbnail_url')
            a.variants             = new_variants
            a.design_prompt        = json.dumps({
                'memory_snapshot': design_data.get('memory_snapshot', {}),
                'model_used':      design_data.get('model_used', ''),
            })
            _flag(a, 'variants')
            _flag(a, 'design_prompt')
            await session.commit()

    background_tasks.add_task(_regen)
    return {'status': 'regenerating', 'asset_id': asset_id,
            'message': 'Generating 2 campaign variants — refresh inbox in ~60s'}


@router.get("/board")
async def pipeline_board(db: AsyncSession = Depends(get_db)):
    """Factory line board — all assets grouped by pipeline stage."""
    from app.models.asset import Asset
    from app.models.project import Project

    assets = (await db.execute(
        select(Asset).order_by(Asset.created_at.desc()).limit(200)
    )).scalars().all()

    projects = {str(p.id): p for p in (await db.execute(select(Project))).scalars().all()}

    STAGE_MAP = {
        "qa_pending":        "Design",
        "qa_failed":         "Arabic QA",
        "approval_pending":  "Approval",
        "approved":          "Scheduled",
        "publishing":        "Scheduled",
        "published":         "Published",
        "rejected":          "Rejected",
    }

    board: dict[str, list] = {
        "Strategy": [], "Copy": [], "Design": [], "Arabic QA": [],
        "Brand QA": [], "Approval": [], "Scheduled": [],
        "Published": [], "Rejected": [],
    }

    for asset in assets:
        stage = STAGE_MAP.get(asset.status, "Copy")
        proj = projects.get(str(asset.project_id))
        card = {
            "id": str(asset.id),
            "project_name": proj.name if proj else "Unknown",
            "project_slug": proj.slug if proj else "",
            "channel": asset.channel,
            "type": asset.type,
            "language": asset.language,
            "copy_ar": (asset.copy_ar or "")[:80],
            "copy_en": (asset.copy_en or "")[:80],
            "thumbnail_url": asset.design_thumbnail_url,
            "status": asset.status,
            "qa_score": asset.qa_score,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }
        if stage in board:
            board[stage].append(card)

    return {
        "stages": [
            {"name": k, "count": len(v), "assets": v}
            for k, v in board.items()
        ]
    }


@router.get("/lab/status")
async def lab_status(db: AsyncSession = Depends(get_db)):
    """Lab control-room: pipeline status, agent cards, health checks, pending approvals."""
    from app.models.asset import Asset
    from app.models.approval import Approval
    from app.config import get_settings
    import os

    # Derive current pipeline state from most recent job
    latest_job = _JOB_HISTORY[0] if _JOB_HISTORY else None
    pipeline_status = "idle"
    if latest_job:
        pipeline_status = latest_job["status"]  # running / done / error

    # Pending approvals with asset previews
    pending_rows = (await db.execute(
        select(Approval, Asset)
        .join(Asset, Asset.id == Approval.asset_id, isouter=True)
        .where(Approval.decision.is_(None))
        .order_by(Approval.created_at.desc())
        .limit(10)
    )).all()
    pending_approvals = []
    for approval, asset in pending_rows:
        pending_approvals.append({
            "id": str(approval.id),
            "asset_id": str(approval.asset_id) if approval.asset_id else None,
            "copy_ar": asset.copy_ar if asset else None,
            "copy_en": asset.copy_en if asset else None,
            "channel": asset.channel if asset else None,
            "thumbnail_url": asset.design_thumbnail_url if asset else None,
        })

    # Recent log entries from latest job's steps
    recent_logs = []
    if latest_job:
        for s in (latest_job.get("steps_history") or [])[-20:]:
            recent_logs.append({
                "ts": s.get("ts"),
                "agent": s.get("agent", ""),
                "step": s.get("step", ""),
                "sources": s.get("data_sources", []),
                "decisions": s.get("decisions", []),
            })

    # Health checks (sync — no external calls)
    settings = get_settings()
    health = {
        "fal_key_set": bool((settings.FAL_KEY or "").strip()),
        "r2_configured": bool(
            (settings.R2_ACCOUNT_ID or "").strip() and
            (settings.R2_ACCESS_KEY_ID or "").strip()
        ),
        "anthropic_key_set": bool((settings.ANTHROPIC_API_KEY or "").strip()),
        "thmanyah_font_exists": os.path.exists(
            "assets/fonts/thmanyah typeface/thmanyahsans/otf/thmanyahsans-Bold.otf"
        ),
    }
    try:
        health["db_tables"] = bool(await db.scalar(
            select(func.count()).select_from(Project)
        ) is not None)
    except Exception:
        health["db_tables"] = False

    return {
        "pipeline_status": pipeline_status,
        "last_run": datetime.fromtimestamp(latest_job["started_at"], tz=timezone.utc).isoformat() if latest_job else None,
        "last_run_project": latest_job.get("project_name", "") if latest_job else "",
        "agents": _build_agent_statuses(latest_job),
        "recent_logs": recent_logs,
        "health": health,
        "pending_approvals": pending_approvals,
        "jobs_today": sum(1 for j in _JOB_HISTORY if j.get("started_at", 0) > time.time() - 86400),
    }
