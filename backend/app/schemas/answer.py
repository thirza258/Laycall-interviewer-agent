from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class AnswerCreate(BaseModel):
    question_id: UUID = Field(..., description="UUID of the question being answered")
    answer: str = Field(..., min_length=1, max_length=5000, description="Candidate's text response")

class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    question_id: UUID
    answer: str
    created_at: datetime