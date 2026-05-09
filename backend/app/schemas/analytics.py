from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class MetricSnapshotCreate(BaseModel):
    project_id: UUID
    asset_id: UUID | None = None
    channel: str
    metric_type: str
    value: Decimal
    date: date
    source: str


class MetricSnapshotRead(MetricSnapshotCreate, ORMBase):
    id: UUID
    created_at: datetime
