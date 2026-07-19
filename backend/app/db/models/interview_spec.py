from typing import Dict, Any
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class InterviewSpec(Base):
    __tablename__ = "interview_specs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # unique=True enforces a 1-to-1 relationship (one spec per interview)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True, unique=True)
    json_data: Mapped[Dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    interview: Mapped["Interview"] = relationship(back_populates="interview_specs")