from typing import Dict, Any
from sqlalchemy import ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

# JSONB on PostgreSQL, plain JSON everywhere else (the test suite runs on
# SQLite). MutableDict is what makes `spec.json_data[key] = value` persist:
# without it SQLAlchemy never sees the in-place mutation and the UPDATE is
# silently skipped, so every write after the first INSERT was lost.
SpecJSON = MutableDict.as_mutable(JSON().with_variant(JSONB(), "postgresql"))


class InterviewSpec(Base):
    __tablename__ = "interview_specs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # unique=True enforces a 1-to-1 relationship (one spec per interview)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True, unique=True)
    json_data: Mapped[Dict[str, Any] | None] = mapped_column(SpecJSON, nullable=True)

    interview: Mapped["Interview"] = relationship(back_populates="interview_specs")
