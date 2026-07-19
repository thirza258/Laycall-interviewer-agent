from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from app.db.base import Base
from app.db.models.job_description import JobDescription


class InterviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        default=InterviewStatus.PENDING, 
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships (cascade delete ensures child records are removed if interview is deleted)
    resumes: Mapped[list["Resume"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    job_descriptions: Mapped[list["JobDescription"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    interview_specs: Mapped[list["InterviewSpec"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship(back_populates="interview", cascade="all, delete-orphan")
    
    def is_completed(self) -> bool:
        return self.status == InterviewStatus.COMPLETED

    def mark_completed(self) -> None:
        self.status = InterviewStatus.COMPLETED