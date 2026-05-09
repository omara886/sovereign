from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Approval, Asset, WeeklyPlan
from app.schemas import ApprovalCreate, ApprovalDecision, ApprovalRead
from app.services.approval_service import handle_approval_decision

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalRead)
async def create_approval(payload: ApprovalCreate, db: AsyncSession = Depends(get_db)):
    if not payload.asset_id and not payload.weekly_plan_id:
        raise HTTPException(400, "asset_id or weekly_plan_id required")
    if payload.asset_id and payload.weekly_plan_id:
        raise HTTPException(400, "only one target allowed")
    if payload.asset_id and not await db.get(Asset, payload.asset_id):
        raise HTTPException(404, "asset not found")
    if payload.weekly_plan_id and not await db.get(WeeklyPlan, payload.weekly_plan_id):
        raise HTTPException(404, "plan not found")
    obj = Approval(**payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("", response_model=list[ApprovalRead])
async def list_approvals(project_id: UUID | None = None, status: str = "pending", db: AsyncSession = Depends(get_db)):
    q = select(Approval)
    if status == "pending":
        q = q.where(Approval.decision.is_(None))
    approvals = (await db.execute(q)).scalars().all()
    if not project_id:
        return approvals
    result = []
    for a in approvals:
        if a.asset_id:
            asset = await db.get(Asset, a.asset_id)
            if asset and asset.project_id == project_id:
                result.append(a)
        elif a.weekly_plan_id:
            plan = await db.get(WeeklyPlan, a.weekly_plan_id)
            if plan and plan.project_id == project_id:
                result.append(a)
    return result


@router.post("/{approval_id}/decide", response_model=ApprovalRead)
async def decide_approval(approval_id: UUID, payload: ApprovalDecision, db: AsyncSession = Depends(get_db)):
    try:
        return await handle_approval_decision(db, str(approval_id), payload.decision, payload.reason, payload.edit_instructions)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
