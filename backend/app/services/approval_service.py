from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Asset, ProjectMemory, PublishJob, WeeklyPlan


async def update_project_memory_negative_example(db: AsyncSession, asset_id: str, reason: str | None) -> None:
    asset = await db.get(Asset, asset_id)
    if not asset:
        return
    memory = (await db.execute(select(ProjectMemory).where(ProjectMemory.project_id == asset.project_id))).scalar_one_or_none()
    if not memory:
        return
    examples = list(memory.rejected_examples or [])
    examples.append({"asset_id": str(asset.id), "channel": asset.channel, "rejection_reason": reason or "rejected", "what_to_avoid": reason or ""})
    memory.rejected_examples = examples
    memory.version = (memory.version or 1) + 1
    await db.commit()


async def handle_approval_decision(db: AsyncSession, approval_id: str, decision: str, reason: str | None = None, edit_instructions: str | None = None) -> Approval:
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise ValueError("approval not found")
    approval.decision = decision
    approval.reason = reason
    approval.edit_instructions = edit_instructions
    approval.decided_at = datetime.now(timezone.utc)

    if approval.asset_id:
        asset = await db.get(Asset, approval.asset_id)
        if asset:
            if decision == "approved":
                asset.status = "approved"
                job = PublishJob(asset_id=asset.id, approval_id=approval.id, channel=asset.channel, scheduled_at=datetime.now(timezone.utc), status="scheduled")
                db.add(job)
            elif decision == "rejected":
                asset.status = "rejected"
                asset.rejection_reason = reason
                await update_project_memory_negative_example(db, str(asset.id), reason)
            elif decision == "edit_requested":
                asset.status = "edit_requested"
                asset.edit_instructions = edit_instructions

    if approval.weekly_plan_id:
        plan = await db.get(WeeklyPlan, approval.weekly_plan_id)
        if plan:
            if decision == "approved":
                plan.status = "approved"
            elif decision == "rejected":
                plan.status = "rejected"
            elif decision == "edit_requested":
                plan.status = "pending_approval"

    await db.commit()
    await db.refresh(approval)
    return approval
