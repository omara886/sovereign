from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class PublishJobCreate(BaseModel):
    asset_id: UUID
    approval_id: UUID
    channel: str
    channel_account_id: str | None = None
    scheduled_at: datetime


class PublishJobRead(ORMBase):
    id: UUID
    asset_id: UUID
    approval_id: UUID
    channel: str
    channel_account_id: str | None
    scheduled_at: datetime
    published_at: datetime | None
    platform_post_id: str | None
    status: str
    error_message: str | None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
