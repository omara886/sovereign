from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class WeeklyPlanBase(BaseModel):
    project_id: UUID
    week_start: date
    objective: str
    funnel_focus: str
    tactics: list = []
    total_budget_estimate: Decimal = Decimal("0")
    rationale: str
    risk_flags: list = []


class WeeklyPlanCreate(WeeklyPlanBase):
    pass


class WeeklyPlanRead(WeeklyPlanBase, ORMBase):
    id: UUID
    status: str
    approval_id: UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime
