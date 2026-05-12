from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class AssetBase(BaseModel):
    project_id: UUID
    weekly_plan_id: UUID | None = None
    tactic_id: str | None = None
    type: str
    channel: str
    language: str
    copy_ar: str | None = None
    copy_en: str | None = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    copy_ar: str | None = None
    copy_en: str | None = None
    status: str | None = None
    design_url: str | None = None
    design_thumbnail_url: str | None = None
    qa_score: Decimal | None = None
    qa_passed: bool | None = None
    qa_notes: list | None = None
    platform_post_id: str | None = None
    rejection_reason: str | None = None
    edit_instructions: str | None = None


class AssetRead(AssetBase, ORMBase):
    id: UUID
    status: str
    design_prompt: str | None
    design_url: str | None
    design_thumbnail_url: str | None
    platform_dimensions: dict | None
    qa_score: Decimal | None
    qa_passed: bool | None
    qa_notes: list
    rejection_reason: str | None
    edit_instructions: str | None
    platform_post_id: str | None
    variants: list
    copy_bilingual: dict | None = None
    created_at: datetime
    updated_at: datetime
