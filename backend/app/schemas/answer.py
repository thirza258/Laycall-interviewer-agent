from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class AnswerCreate(BaseModel):
    question_id: int = Field(..., description="ID of the question being answered")
    answer: str = Field(..., min_length=1, max_length=5000, description="Candidate's text response")

class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer: str
    created_at: datetime