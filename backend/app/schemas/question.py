from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class QuestionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "question_id": "550e8400-e29b-41d4-a716-446655440000",
                "question": "Tell me about a time you optimized a slow database query."
            }
        }
    )

    question_id: UUID = Field(..., alias="question_id")
    question: str = Field(...)