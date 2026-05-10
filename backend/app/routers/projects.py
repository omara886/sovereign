from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Approval, Asset, BrandMemory, Project, ProjectMemory, WeeklyPlan
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Project).order_by(Project.created_at.desc()))).scalars().all()


@router.post("", response_model=ProjectRead)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    obj = Project(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Project, project_id)
    if not obj:
        raise HTTPException(404, "project not found")
    return obj


@router.get("/{project_ref}/status")
async def get_project_status(project_ref: str, db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.slug == project_ref))).scalar_one_or_none()
    if not project:
        try:
            project = await db.get(Project, UUID(project_ref))
        except Exception:
            project = None
    if not project:
        raise HTTPException(404, "project not found")

    pid = project.id
    brand = (await db.execute(select(BrandMemory).where(BrandMemory.project_id == pid))).scalar_one_or_none()
    memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == pid))).scalar_one_or_none()
    latest_plan = (await db.execute(
        select(WeeklyPlan).where(WeeklyPlan.project_id == pid).order_by(WeeklyPlan.week_start.desc(), WeeklyPlan.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    pending_approvals = await db.scalar(
        select(func.count(Approval.id))
        .join(Asset, Asset.id == Approval.asset_id)
        .where(Asset.project_id == pid, Approval.decision.is_(None))
    ) or 0
    published_assets = await db.scalar(
        select(func.count(Asset.id)).where(Asset.project_id == pid, Asset.status == "published")
    ) or 0

    return {
        "project_id": str(pid),
        "slug": project.slug,
        "name": project.name,
        "has_logo": bool(brand and brand.logo_url),
        "has_memory": memory is not None,
        "has_plan": latest_plan is not None,
        "plan_status": latest_plan.status if latest_plan else None,
        "plan_id": str(latest_plan.id) if latest_plan else None,
        "pending_approvals": pending_approvals,
        "published_assets": published_assets,
        "next_action": (
            "upload_logo" if not brand or not brand.logo_url else
            "generate_plan" if not latest_plan else
            "approve_plan" if latest_plan.status == "pending_approval" else
            "review_inbox" if pending_approvals > 0 else
            "running" if latest_plan.status in ("approved", "executing") else
            "complete"
        ),
    }


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Project, project_id)
    if not obj:
        raise HTTPException(404, "project not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj
