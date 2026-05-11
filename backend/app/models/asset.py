import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:
    Vector = None


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    weekly_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("weekly_plans.id"))
    tactic_id: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    copy_ar: Mapped[str | None] = mapped_column(Text)
    copy_en: Mapped[str | None] = mapped_column(Text)
    copy_bilingual: Mapped[dict | None] = mapped_column(JSONB)
    design_prompt: Mapped[str | None] = mapped_column(Text)
    design_url: Mapped[str | None] = mapped_column(Text)
    design_thumbnail_url: Mapped[str | None] = mapped_column(Text)
    platform_dimensions: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="generating")
    qa_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    qa_passed: Mapped[bool | None] = mapped_column(Boolean)
    qa_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    edit_instructions: Mapped[str | None] = mapped_column(Text)
    platform_post_id: Mapped[str | None] = mapped_column(Text)
    variants: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536) if Vector else JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
