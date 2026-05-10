from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.approval import Approval
from app.models.metric_snapshot import MetricSnapshot
from app.models.project import Project
from app.models.project_memory import ProjectMemory
from app.models.publish_job import PublishJob

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Cache TTL in seconds for expensive read-only endpoints
_CACHE = "public, max-age=60, stale-while-revalidate=30"


@router.get("/summary")
async def get_metrics_summary(db: AsyncSession = Depends(get_db)):
    # Single query with multiple counts instead of 3 separate queries
    published = await db.scalar(select(func.count(Asset.id)).where(Asset.status == "published")) or 0
    pending   = await db.scalar(select(func.count(Approval.id)).where(Approval.decision.is_(None))) or 0
    total     = await db.scalar(select(func.count(Asset.id))) or 0
    return JSONResponse(
        {"published_assets": published, "pending_approvals": pending, "total_assets_generated": total},
        headers={"cache-control": _CACHE},
    )


@router.get("/assets")
async def get_asset_metrics(
    project_id: UUID | None = Query(default=None),
    project_slug: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    if not project_id and not project_slug:
        raise HTTPException(400, "project_id or project_slug required")

    if project_slug and not project_id:
        project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "project not found")
        project_id = project.id

    assets = (
        await db.execute(
            select(Asset)
            .where(Asset.project_id == project_id, Asset.status == "published")
            .order_by(desc(Asset.updated_at))
            .limit(limit)
        )
    ).scalars().all()

    if not assets:
        return JSONResponse([], headers={"cache-control": _CACHE})

    asset_ids = [a.id for a in assets]

    # Batch fetch publish jobs — one query, not N queries
    pj_rows = (
        await db.execute(
            select(PublishJob)
            .where(PublishJob.asset_id.in_(asset_ids))
            .order_by(desc(PublishJob.published_at))
        )
    ).scalars().all()
    pj_by_asset: dict = {}
    for pj in pj_rows:
        if str(pj.asset_id) not in pj_by_asset:
            pj_by_asset[str(pj.asset_id)] = pj

    # Batch fetch metric snapshots — one query, not N queries
    snap_rows = (
        await db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.asset_id.in_(asset_ids))
            .order_by(desc(MetricSnapshot.date))
        )
    ).scalars().all()
    snaps_by_asset: dict[str, dict] = {}
    for snap in snap_rows:
        aid = str(snap.asset_id)
        if aid not in snaps_by_asset:
            snaps_by_asset[aid] = {}
        key = snap.metric_type.lower()
        if key not in snaps_by_asset[aid]:
            snaps_by_asset[aid][key] = float(snap.value)

    results = []
    for asset in assets:
        aid = str(asset.id)
        pj = pj_by_asset.get(aid)
        snaps = snaps_by_asset.get(aid, {})
        results.append({
            "asset_id": aid,
            "channel": asset.channel,
            "type": asset.type,
            "published_at": pj.published_at.isoformat() if pj and pj.published_at else None,
            "platform_post_id": (pj.platform_post_id if pj else None) or asset.platform_post_id,
            "thumbnail_url": asset.design_thumbnail_url or asset.design_url,
            "metrics": {
                "impressions": snaps.get("impressions", 0),
                "clicks": snaps.get("clicks", 0),
                "engagement_rate": snaps.get("engagement_rate", 0),
            },
        })

    return JSONResponse(results, headers={"cache-control": _CACHE})


@router.get("/weekly-summary")
async def weekly_summary(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Project, ProjectMemory)
            .join(ProjectMemory, ProjectMemory.project_id == Project.id)
            .where(Project.status == "active", ProjectMemory.performance_learnings.is_not(None))
            .order_by(Project.priority.asc())
        )
    ).all()

    if not rows:
        return JSONResponse({"projects": []}, headers={"cache-control": _CACHE})

    project_ids = [r[0].id for r in rows]

    # Batch: one query for latest published asset per project
    latest_assets = (
        await db.execute(
            select(Asset)
            .where(Asset.project_id.in_(project_ids), Asset.status == "published")
            .order_by(desc(Asset.updated_at))
        )
    ).scalars().all()
    latest_by_project: dict = {}
    for a in latest_assets:
        pid = str(a.project_id)
        if pid not in latest_by_project:
            latest_by_project[pid] = a

    projects = []
    for project, memory in rows:
        learnings = (memory.performance_learnings or "").strip()
        if not learnings:
            continue
        latest = latest_by_project.get(str(project.id))
        projects.append({
            "name": project.name,
            "slug": project.slug,
            "learnings": learnings,
            "top_asset_url": (latest.design_thumbnail_url or latest.design_url) if latest else None,
        })

    return JSONResponse({"projects": projects}, headers={"cache-control": _CACHE})
