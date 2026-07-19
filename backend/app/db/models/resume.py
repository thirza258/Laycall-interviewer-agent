from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    interview: Mapped["Interview"] = relationship(back_populates="resumes")