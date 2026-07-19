from pydantic import BaseModel, Field
from uuid import UUID

class QuestionResponse(BaseModel):
    question_id: UUID = Field(..., alias="question_id")
    question: str = Field(...)
    
    class Config:
        populate_by_name = True  # Allows using "question_id" in JSON
        json_schema_extra = {
            "example": {
                "question_id": "550e8400-e29b-41d4-a716-446655440000",
                "question": "Tell me about a time you optimized a slow database query."
            }
        }