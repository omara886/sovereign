from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.approval import Approval
from app.models.metric_snapshot import MetricSnapshot
from app.models.project import Project
from app.models.publish_job import PublishJob

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
async def get_metrics_summary(db: AsyncSession = Depends(get_db)):
    published = await db.scalar(select(func.count(Asset.id)).where(Asset.status == "published")) or 0
    pending = await db.scalar(select(func.count(Approval.id)).where(Approval.decision.is_(None))) or 0
    total_assets = await db.scalar(select(func.count(Asset.id))) or 0
    return {
        "published_assets": published,
        "pending_approvals": pending,
        "total_assets_generated": total_assets,
    }


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
            .order_by(desc(Asset.updated_at), desc(Asset.created_at))
            .limit(limit)
        )
    ).scalars().all()

    results: list[dict] = []
    for asset in assets:
        publish_job = (
            await db.execute(
                select(PublishJob)
                .where(PublishJob.asset_id == asset.id)
                .order_by(desc(PublishJob.published_at), desc(PublishJob.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        snapshots = (
            await db.execute(
                select(MetricSnapshot)
                .where(MetricSnapshot.asset_id == asset.id)
                .order_by(desc(MetricSnapshot.date), desc(MetricSnapshot.created_at))
            )
        ).scalars().all()

        metrics = {"impressions": 0, "clicks": 0, "engagement_rate": 0}
        latest_by_type: dict[str, MetricSnapshot] = {}
        for snapshot in snapshots:
            key = snapshot.metric_type.lower()
            if key not in latest_by_type:
                latest_by_type[key] = snapshot
        for metric_key in metrics:
            snap = latest_by_type.get(metric_key)
            if snap:
                metrics[metric_key] = float(snap.value)

        results.append(
            {
                "asset_id": str(asset.id),
                "channel": asset.channel,
                "type": asset.type,
                "published_at": publish_job.published_at.isoformat() if publish_job and publish_job.published_at else None,
                "platform_post_id": publish_job.platform_post_id if publish_job else asset.platform_post_id,
                "thumbnail_url": asset.design_thumbnail_url or asset.design_url,
                "metrics": metrics,
            }
        )

    return results
