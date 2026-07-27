from pydantic import BaseModel, Field, ConfigDict

class QuestionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "question_id": 1,
                "question": "Tell me about a time you optimized a slow database query."
            }
        }
    )

    question_id: int = Field(..., alias="question_id")
    question: str = Field(...)