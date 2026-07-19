from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class JobDescriptionCreate(BaseModel):
    raw_text: str = Field(..., min_length=10, description="Full job description text")

class InterviewCreate(BaseModel):
    job_description: str = Field(..., min_length=10, description="Job description to store")
    resume_id: int = Field(..., gt=0, description="ID of the resume to associate with this interview")

class JobDescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    interview_id: int
    raw_text: str
    created_at: datetime

class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime
    job_description: Optional[JobDescriptionResponse] = None