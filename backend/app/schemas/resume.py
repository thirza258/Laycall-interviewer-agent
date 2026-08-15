from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class ResumeCreate(BaseModel):
    """
    Schema for resume creation/upload request.

    Note: The actual file upload is handled via FastAPI's UploadFile
    in the endpoint, not through this schema. This schema validates
    the form fields (like interview_id).
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "interview_id": 1
            }
        }
    )

    interview_id: int = Field(
        ...,
        gt=0,
        description="ID of the interview to associate this resume with"
    )


class ResumeResponse(BaseModel):
    """
    Schema for a single resume record returned from the API.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 42,
                "interview_id": 1,
                "file_path": "resumes/1/a3f8b2c1d4e5.pdf",
                "raw_text": "John Doe\nSoftware Engineer\nExperience: ...",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )

    id: int = Field(..., description="Unique resume identifier")
    interview_id: int = Field(..., description="Associated interview ID")
    file_path: str = Field(..., description="MinIO object path (e.g., 'resumes/1/abc123.pdf')")
    raw_text: Optional[str] = Field(None, description="Extracted plain text from the resume")
    created_at: datetime = Field(..., description="Timestamp when record was created")


class ResumeUploadResponse(BaseModel):
    """
    Wrapper schema for the resume upload success response.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "message": "Resume uploaded successfully",
                "resume": {
                    "id": 42,
                    "interview_id": 1,
                    "file_path": "resumes/1/a3f8b2c1d4e5.pdf",
                    "raw_text": "John Doe\nSoftware Engineer...",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                "questions_generated": 12,
                "generation_error": None
            }
        }
    )

    message: str = Field(..., description="Success message")
    resume: ResumeResponse = Field(..., description="The created resume record")
    questions_generated: int = Field(
        0,
        description="Number of interview questions generated for this upload"
    )
    generation_error: Optional[str] = Field(
        None,
        description="Why question generation failed, if it did. The interview retries on the first question request."
    )


class ResumeListResponse(BaseModel):
    """
    Schema for listing multiple resumes (for future GET endpoint).
    """
    model_config = ConfigDict(from_attributes=True)
    
    resumes: list[ResumeResponse]
    total: int = Field(..., description="Total number of resumes")


class ResumeUpdate(BaseModel):
    """
    Schema for partial updates to a resume record.
    All fields optional for PATCH requests.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "raw_text": "Updated resume content..."
            }
        }
    )

    raw_text: Optional[str] = Field(None, description="Updated extracted text")