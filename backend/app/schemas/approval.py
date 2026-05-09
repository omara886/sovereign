from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class ApprovalCreate(BaseModel):
    asset_id: UUID | None = None
    weekly_plan_id: UUID | None = None
    approver_id: str = "founder"


class ApprovalDecision(BaseModel):
    decision: str
    reason: str | None = None
    edit_instructions: str | None = None


class ApprovalRead(ORMBase):
    id: UUID
    asset_id: UUID | None
    weekly_plan_id: UUID | None
    approver_id: str
    decision: str | None
    reason: str | None
    edit_instructions: str | None
    notification_channels: list[str]
    notification_sent_at: datetime | None
    decided_at: datetime | None
    created_at: datetime
