from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.asset import Asset
from app.models.approval import Approval

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
