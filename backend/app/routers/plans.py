from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, WeeklyPlan
from app.schemas import WeeklyPlanCreate, WeeklyPlanRead

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[WeeklyPlanRead])
async def list_plans(
    project_id: UUID | None = None,
    project_slug: str | None = Query(default=None),
    week_start: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    q = select(WeeklyPlan)
    if project_id:
        q = q.where(WeeklyPlan.project_id == project_id)
    if project_slug:
        project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "project not found")
        q = q.where(WeeklyPlan.project_id == project.id)
    if week_start:
        q = q.where(WeeklyPlan.week_start == week_start)
    return (await db.execute(q)).scalars().all()


@router.get("/current/{project_slug}", response_model=WeeklyPlanRead)
async def get_current_plan(project_slug: str, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_slug))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "project not found")
    q = (
        select(WeeklyPlan)
        .where(WeeklyPlan.project_id == project.id)
        .order_by(desc(WeeklyPlan.week_start), desc(WeeklyPlan.created_at))
    )
    obj = (await db.execute(q)).scalars().first()
    if not obj:
        raise HTTPException(404, "plan not found")
    return obj


@router.get("/{plan_id}", response_model=WeeklyPlanRead)
async def get_plan(plan_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(WeeklyPlan, plan_id)
    if not obj:
        raise HTTPException(404, "plan not found")
    return obj


@router.post("", response_model=WeeklyPlanRead)
async def create_plan(payload: WeeklyPlanCreate, db: AsyncSession = Depends(get_db)):
    obj = WeeklyPlan(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj
