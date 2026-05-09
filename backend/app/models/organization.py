import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plan_type: Mapped[str] = mapped_column(Text, nullable=False, default="internal")
    owner_email: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(Text)
    resend_from_email: Mapped[str | None] = mapped_column(Text, default="sovereign@notifications.ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
