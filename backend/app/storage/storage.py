import uuid
import mimetypes
from pathlib import Path
from io import BytesIO
from fastapi import HTTPException
from app.core.minio_client import MinIOClient

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024 

def validate_file(filename: str, file_size: int | None, content_type: str | None) -> None:
    """Validate file type and size using metadata only (no stream reading)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file_size and file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

def generate_object_name(interview_id: int, filename: str) -> str:
    """Generate a unique MinIO object path."""
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"resumes/{interview_id}/{unique_name}"

def upload_to_minio(
    file_bytes: bytes,
    filename: str,
    interview_id: int,
    content_type: str | None = None
) -> tuple[str, str]:
    """
    Upload raw file bytes to MinIO.
    
    Args:
        file_bytes: The actual file content (already read from UploadFile)
        filename: Original filename for extension detection
        interview_id: For organizing object path
        content_type: Optional MIME type (auto-detected if None)
    
    Returns:
        (object_name, public_url)
    """
    file_size = len(file_bytes)
    validate_file(filename, file_size, content_type)
    
    object_name = generate_object_name(interview_id, filename)
    
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
    file_stream = BytesIO(file_bytes)
    
    public_url = MinIOClient.upload_fileobj(
        file_obj=file_stream,
        object_name=object_name,
        file_size=file_size,
        content_type=content_type
    )
    
    return object_name, public_url