from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HrInterview(Base):
    __tablename__ = "hr_interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    turns: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
