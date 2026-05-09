from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class OrganizationCreate(BaseModel):
    name: str
    owner_email: str
    plan_type: str = "internal"
    telegram_chat_id: str | None = None


class OrganizationRead(ORMBase):
    id: UUID
    name: str
    plan_type: str
    owner_email: str
    telegram_chat_id: str | None
    resend_from_email: str | None
    created_at: datetime
    updated_at: datetime
