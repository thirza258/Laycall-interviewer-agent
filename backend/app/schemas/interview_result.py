from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class InterviewResultsResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "interview_id": 1,
                "status": "completed",
                "overall_score": 82,
                "technical_score": 85,
                "communication_score": 78,
                "strengths": [
                    "Strong grasp of async/await patterns",
                    "Clear explanation of dependency injection"
                ],
                "weaknesses": [
                    "Limited experience with distributed systems",
                    "Could provide more concrete metrics in answers"
                ],
                "recommendations": [
                    "Proceed to technical deep-dive round",
                    "Assign system design prep resources"
                ],
                "completed_at": "2024-01-15T16:30:00Z"
            }
        }
    )

    interview_id: int
    status: str
    overall_score: Optional[int] = Field(None, ge=0, le=100)
    technical_score: Optional[int] = Field(None, ge=0, le=100)
    communication_score: Optional[int] = Field(None, ge=0, le=100)
    strengths: list[str] = Field(default=[])
    weaknesses: list[str] = Field(default=[])
    recommendations: list[str] = Field(default=[])
    completed_at: Optional[datetime] = None