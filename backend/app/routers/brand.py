from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BrandMemory
from app.schemas import BrandMemoryRead, BrandMemoryUpdate

router = APIRouter(tags=["brand"])


@router.get("/projects/{project_id}/brand", response_model=BrandMemoryRead)
async def get_brand(project_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    return obj


@router.patch("/projects/{project_id}/brand", response_model=BrandMemoryRead)
async def patch_brand(project_id: UUID, payload: BrandMemoryUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/projects/{project_id}/brand/approve", response_model=BrandMemoryRead)
async def approve_brand(project_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    obj.is_provisional = False
    obj.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(obj)
    return obj
