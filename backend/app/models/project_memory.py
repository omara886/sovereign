import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectMemory(Base):
    __tablename__ = "project_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    icp: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    positioning: Mapped[str | None] = mapped_column(Text)
    offers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tone: Mapped[str | None] = mapped_column(Text)
    languages: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=["ar", "en"])
    funnel_goals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    approved_examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rejected_examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    performance_learnings: Mapped[str | None] = mapped_column(Text)
    brand_brief: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
