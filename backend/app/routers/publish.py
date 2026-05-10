from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Asset, PublishJob
from app.schemas import PublishJobRead

router = APIRouter(prefix="/publish-jobs", tags=["publish-jobs"])


@router.get("", response_model=list[PublishJobRead])
async def list_publish_jobs(project_id: UUID | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    q = select(PublishJob).order_by(PublishJob.created_at.desc())
    if project_id:
        q = q.join(Asset, Asset.id == PublishJob.asset_id).where(Asset.project_id == project_id)
    return (await db.execute(q)).scalars().all()
