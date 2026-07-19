from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    answer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("answers.id", ondelete="CASCADE"),
        index=True,
        unique=True  
    )
    technical_score: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("technical_score >= 0 AND technical_score <= 10"),
        comment="Score 0-10 for technical accuracy"
    )
    communication_score: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("communication_score >= 0 AND communication_score <= 10"),
        comment="Score 0-10 for communication clarity"
    )
    feedback: Mapped[str] = mapped_column(Text, comment="Constructive feedback for the candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answer: Mapped["Answer"] = relationship(back_populates="evaluation")
    