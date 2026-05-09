import asyncio
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Riyadh")


def _run_async(coro):
    """Run a coroutine from the background scheduler thread."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)


async def _monday_strategy_run():
    """Monday 08:00 Riyadh — Strategy Agent generates weekly plans for all active projects."""
    from app.database import AsyncSessionLocal
    from app.agents.strategy import StrategyAgent
    from app.agents.approval_agent import ApprovalAgent
    from app.models.project import Project
    from sqlalchemy import select

    logger.info("scheduler: monday_strategy_run started")
    async with AsyncSessionLocal() as db:
        projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
        strategy = StrategyAgent()
        for project in projects:
            try:
                week_start = _current_week_monday()
                plan_data = await strategy.create_plan(db, str(project.id), week_start)
                if "error" not in plan_data:
                    from app.models.weekly_plan import WeeklyPlan
                    plan = WeeklyPlan(
                        project_id=project.id,
                        week_start=week_start,
                        objective=plan_data.get("objective", ""),
                        funnel_focus=plan_data.get("funnel_focus", "awareness"),
                        tactics=plan_data.get("tactics", []),
                        total_budget_estimate=plan_data.get("total_budget_estimate", 0),
                        rationale=plan_data.get("rationale", ""),
                        risk_flags=plan_data.get("risk_flags", []),
                        status="draft",
                    )
                    db.add(plan)
                    await db.commit()
                    logger.info("scheduler: plan created for project %s", project.slug)
            except Exception as exc:
                logger.error("scheduler: strategy failed for project %s: %s", project.slug, exc)


async def _monday_plan_notification():
    """Monday 09:00 Riyadh — Notify founder of pending plan approvals."""
    from app.database import AsyncSessionLocal
    from app.agents.approval_agent import ApprovalAgent
    from app.models.weekly_plan import WeeklyPlan
    from app.models.project import Project
    from sqlalchemy import select

    logger.info("scheduler: monday_plan_notification started")
    approval_agent = ApprovalAgent()
    async with AsyncSessionLocal() as db:
        week_start = _current_week_monday()
        plans = (await db.execute(
            select(WeeklyPlan).where(WeeklyPlan.week_start == week_start, WeeklyPlan.status == "draft")
        )).scalars().all()
        for plan in plans:
            project = await db.get(Project, plan.project_id)
            if project:
                try:
                    await approval_agent.notify_plan_ready(db, str(project.id), project.name, plan)
                    logger.info("scheduler: plan notification sent for %s", project.slug)
                except Exception as exc:
                    logger.error("scheduler: plan notification failed for %s: %s", project.slug, exc)


async def _process_publish_queue():
    """Every 5 min — pick up ready PublishJobs and execute them."""
    from app.database import AsyncSessionLocal
    from app.agents.publishing import PublishingAgent
    from app.models.publish_job import PublishJob
    from sqlalchemy import select
    from datetime import datetime, timezone

    publisher = PublishingAgent()
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        ready_jobs = (await db.execute(
            select(PublishJob).where(
                PublishJob.status == "scheduled",
                PublishJob.scheduled_at <= now,
                PublishJob.retry_count < PublishJob.max_retries,
            ).limit(10)
        )).scalars().all()
        for job in ready_jobs:
            try:
                result = await publisher.publish(db, str(job.id))
                logger.info("scheduler: publish job %s result: %s", job.id, result.get("status"))
            except Exception as exc:
                logger.error("scheduler: publish job %s failed: %s", job.id, exc)


async def _sunday_analytics_run():
    """Sunday 18:00 Riyadh — Analytics Agent generates weekly report."""
    from app.database import AsyncSessionLocal
    from app.agents.analytics_agent import AnalyticsAgent
    from app.models.project import Project
    from app.models.asset import Asset
    from app.models.metric_snapshot import MetricSnapshot
    from sqlalchemy import select

    logger.info("scheduler: sunday_analytics_run started")
    async with AsyncSessionLocal() as db:
        projects = (await db.execute(select(Project).where(Project.status == "active"))).scalars().all()
        analytics = AnalyticsAgent()
        week_end = date.today()
        week_start = week_end - timedelta(days=6)
        for project in projects:
            try:
                assets = (await db.execute(
                    select(Asset).where(
                        Asset.project_id == project.id,
                        Asset.status == "published",
                    ).limit(20)
                )).scalars().all()
                metrics = (await db.execute(
                    select(MetricSnapshot).where(
                        MetricSnapshot.project_id == project.id,
                        MetricSnapshot.date >= week_start,
                    ).limit(50)
                )).scalars().all()
                published_assets = [
                    {"id": str(a.id), "channel": a.channel, "type": a.type, "copy_ar": a.copy_ar}
                    for a in assets
                ]
                metrics_data = [
                    {"metric_type": m.metric_type, "value": float(m.value), "channel": m.channel, "date": str(m.date)}
                    for m in metrics
                ]
                await analytics.run_weekly_report(
                    db, str(project.id), project.name,
                    metrics_data, published_assets, week_start, week_end
                )
                logger.info("scheduler: analytics report sent for %s", project.slug)
            except Exception as exc:
                logger.error("scheduler: analytics failed for %s: %s", project.slug, exc)


def _current_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def register_jobs() -> None:
    scheduler.add_job(
        lambda: _run_async(_monday_strategy_run()),
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="monday_strategy_run",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_async(_monday_plan_notification()),
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="monday_plan_notification",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_async(_process_publish_queue()),
        IntervalTrigger(minutes=5),
        id="process_publish_queue",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_async(_sunday_analytics_run()),
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="sunday_analytics_run",
        replace_existing=True,
    )


register_jobs()
