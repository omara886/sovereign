import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BrandMemory(Base):
    __tablename__ = "brand_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    color_palette: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    typography: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    arabic_font_url: Mapped[str | None] = mapped_column(Text)
    visual_style: Mapped[str | None] = mapped_column(Text)
    image_style: Mapped[str | None] = mapped_column(Text)
    brand_voice: Mapped[str | None] = mapped_column(Text)
    dos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    donts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    templates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rejected_styles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_provisional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
