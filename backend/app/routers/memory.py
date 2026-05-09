from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ProjectMemory
from app.schemas import ProjectMemoryRead, ProjectMemoryUpdate

router = APIRouter(tags=["memory"])


@router.get("/projects/{project_id}/memory", response_model=ProjectMemoryRead)
async def get_memory(project_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "memory not found")
    return obj


@router.patch("/projects/{project_id}/memory", response_model=ProjectMemoryRead)
async def patch_memory(project_id: UUID, payload: ProjectMemoryUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "memory not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj
