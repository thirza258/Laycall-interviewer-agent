from datetime import datetime
import uuid
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base



class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True
    )
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped["Question"] = relationship(back_populates="answers")
    
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan"
    )