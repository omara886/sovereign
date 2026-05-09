from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import WeeklyPlan
from app.schemas import WeeklyPlanCreate, WeeklyPlanRead

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[WeeklyPlanRead])
async def list_plans(project_id: UUID | None = None, week_start: date | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    q = select(WeeklyPlan)
    if project_id:
        q = q.where(WeeklyPlan.project_id == project_id)
    if week_start:
        q = q.where(WeeklyPlan.week_start == week_start)
    return (await db.execute(q)).scalars().all()


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
