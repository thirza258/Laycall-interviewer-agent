from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interview: Mapped["Interview"] = relationship(back_populates="resumes")