from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    question_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    difficulty: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    interview: Mapped["Interview"] = relationship(
        back_populates="questions"
    )
    
    answers: Mapped[list["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")