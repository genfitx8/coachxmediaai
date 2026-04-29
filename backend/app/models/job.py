import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, ForeignKey, func, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
    media: Mapped[Optional["Media"]] = relationship("Media")  # type: ignore[name-defined]
