from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

class AnswerCreate(BaseModel):
    question_id: int = Field(..., gt=0, description="ID of the question being answered")
    answer: str = Field(..., min_length=1, max_length=5000, description="Candidate's text response")

    @field_validator("answer")
    @classmethod
    def strip_answer(cls, value: str) -> str:
        """Validate what actually gets stored.

        The answer is persisted stripped, so a whitespace-only submission used
        to satisfy min_length here and land in the database as an empty string.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("answer must contain non-whitespace text")
        return stripped

class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer: str
    created_at: datetime