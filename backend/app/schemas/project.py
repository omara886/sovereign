from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class ProjectBase(BaseModel):
    org_id: UUID
    name: str
    slug: str
    business_model: str
    primary_goal: str
    website_url: str | None = None
    priority: int = 1
    channels: list = []


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    primary_goal: str | None = None
    website_url: str | None = None
    priority: int | None = None
    channels: list | None = None


class ProjectRead(ProjectBase, ORMBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
