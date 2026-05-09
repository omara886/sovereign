from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMBase


class ProjectMemoryBase(BaseModel):
    icp: dict = {}
    positioning: str | None = None
    offers: list = []
    tone: str | None = None
    languages: list[str] = ["ar", "en"]
    funnel_goals: dict = {}
    constraints: dict = {}
    approved_examples: list = []
    rejected_examples: list = []
    performance_learnings: str | None = None


class ProjectMemoryCreate(ProjectMemoryBase):
    project_id: UUID


class ProjectMemoryUpdate(BaseModel):
    icp: dict | None = None
    positioning: str | None = None
    offers: list | None = None
    tone: str | None = None
    languages: list[str] | None = None
    funnel_goals: dict | None = None
    constraints: dict | None = None
    approved_examples: list | None = None
    rejected_examples: list | None = None
    performance_learnings: str | None = None


class ProjectMemoryRead(ProjectMemoryBase, ORMBase):
    id: UUID
    project_id: UUID
    version: int
    updated_at: datetime


class BrandMemoryBase(BaseModel):
    logo_url: str | None = None
    color_palette: dict = {}
    typography: dict = {}
    arabic_font_url: str | None = None
    visual_style: str | None = None
    image_style: str | None = None
    brand_voice: str | None = None
    dos: list = []
    donts: list = []
    templates: list = []
    rejected_styles: list = []


class BrandMemoryCreate(BrandMemoryBase):
    project_id: UUID


class BrandMemoryUpdate(BaseModel):
    logo_url: str | None = None
    color_palette: dict | None = None
    typography: dict | None = None
    arabic_font_url: str | None = None
    visual_style: str | None = None
    image_style: str | None = None
    brand_voice: str | None = None
    dos: list | None = None
    donts: list | None = None
    templates: list | None = None
    rejected_styles: list | None = None
    is_provisional: bool | None = None


class BrandMemoryRead(BrandMemoryBase, ORMBase):
    id: UUID
    project_id: UUID
    is_provisional: bool
    approved_at: datetime | None
    version: int
    updated_at: datetime
