from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import BrandMemory
from app.models.project import Project
from app.schemas import BrandMemoryRead, BrandMemoryUpdate

router = APIRouter(tags=["brand"])


async def _resolve_project_id(project_ref: str, db: AsyncSession) -> str:
    proj = (await db.execute(select(Project).where(Project.slug == project_ref))).scalar_one_or_none()
    if proj:
        return str(proj.id)
    try:
        from uuid import UUID
        UUID(project_ref)
        return project_ref
    except ValueError:
        raise HTTPException(404, f"project '{project_ref}' not found")


@router.get("/projects/{project_ref}/brand", response_model=BrandMemoryRead)
async def get_brand(project_ref: str, db: AsyncSession = Depends(get_db)):
    project_id = await _resolve_project_id(project_ref, db)
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    return obj


@router.patch("/projects/{project_ref}/brand", response_model=BrandMemoryRead)
async def patch_brand(project_ref: str, payload: BrandMemoryUpdate, db: AsyncSession = Depends(get_db)):
    project_id = await _resolve_project_id(project_ref, db)
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/projects/{project_ref}/brand/approve", response_model=BrandMemoryRead)
async def approve_brand(project_ref: str, db: AsyncSession = Depends(get_db)):
    project_id = await _resolve_project_id(project_ref, db)
    obj = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "brand not found")
    obj.is_provisional = False
    obj.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(obj)
    return obj
