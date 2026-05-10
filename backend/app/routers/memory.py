from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ProjectMemory
from app.models.project import Project
from app.schemas import ProjectMemoryRead, ProjectMemoryUpdate

router = APIRouter(tags=["memory"])


async def _resolve_project_id(project_ref: str, db: AsyncSession) -> str:
    """Accept either a UUID or a project slug and return the project UUID."""
    # Try slug first (most common case from frontend)
    proj = (await db.execute(select(Project).where(Project.slug == project_ref))).scalar_one_or_none()
    if proj:
        return str(proj.id)
    # Fall back to treating it as UUID
    try:
        from uuid import UUID
        UUID(project_ref)
        return project_ref
    except ValueError:
        raise HTTPException(404, f"project '{project_ref}' not found")


@router.get("/projects/{project_ref}/memory", response_model=ProjectMemoryRead)
async def get_memory(project_ref: str, db: AsyncSession = Depends(get_db)):
    project_id = await _resolve_project_id(project_ref, db)
    obj = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "memory not found")
    return obj


@router.patch("/projects/{project_ref}/memory", response_model=ProjectMemoryRead)
async def patch_memory(project_ref: str, payload: ProjectMemoryUpdate, db: AsyncSession = Depends(get_db)):
    project_id = await _resolve_project_id(project_ref, db)
    obj = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == project_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "memory not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj
