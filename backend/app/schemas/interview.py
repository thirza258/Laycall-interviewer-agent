from pydantic import BaseModel, Field, ConfigDict, StringConstraints
from datetime import datetime
from typing import Annotated, Optional

JobDescriptionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10)]

class JobDescriptionCreate(BaseModel):
    raw_text: JobDescriptionText = Field(..., description="Full job description text")

class InterviewCreate(BaseModel):
    job_description: JobDescriptionText = Field(..., description="Job description to store")
    resume_id: Optional[int] = Field(None, gt=0, description="ID of the resume to associate with this interview")

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
