import logging
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.resume import Resume
from app.db.models.interview import Interview
from app.schemas.resume import ResumeResponse, ResumeUploadResponse
from app.storage.storage import upload_to_minio, validate_file
from app.services.resume_parser import extract_resume_text_from_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resumes", tags=["resumes"])

@router.post(
    "",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume",
    description="Upload a PDF or DOCX resume file to MinIO and associate it with an interview."
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    interview_id: int = Form(..., description="ID of the interview to associate with"),
    db: AsyncSession = Depends(get_db)
) -> ResumeUploadResponse:
    """
    Upload a resume file to MinIO, extract its text, and create a database record.
    """
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview with ID {interview_id} not found"
        )
    
    try:
        validate_file(file.filename, file.size, file.content_type)
    except HTTPException:
        raise

    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process uploaded file"
        )
    
    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    try:
        object_name, public_url = upload_to_minio(
            file_bytes=file_content,
            filename=file.filename,
            interview_id=interview_id,
            content_type=file.content_type
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )
    
    raw_text = extract_resume_text_from_bytes(file_content, file.filename)
    
    new_resume = Resume(
        interview_id=interview_id,
        file_path=object_name, 
        raw_text=raw_text if raw_text else None
    )
    
    db.add(new_resume)
    await db.commit()
    await db.refresh(new_resume)
    
    logger.info(
        f"Resume uploaded: id={new_resume.id}, "
        f"object={object_name}, size={len(file_content)} bytes, "
        f"text_length={len(raw_text) if raw_text else 0}"
    )
    
    return ResumeUploadResponse(
        message="Resume uploaded successfully",
        resume=ResumeResponse.model_validate(new_resume)
    )