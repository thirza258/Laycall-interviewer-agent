import logging
from pathlib import Path
from io import BytesIO
from PyPDF2 import PdfReader 
from docx import Document
from app.core.minio_client import MinIOClient

logger = logging.getLogger(__name__)

def extract_text_from_pdf_bytes(content: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from PDF bytes: {e}")
        return ""

def extract_text_from_docx_bytes(content: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        doc = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX bytes: {e}")
        return ""

def extract_text_from_file_path(file_path: str) -> str:
    """Extract text from a local file path using PyPDF2."""
    ext = Path(file_path).suffix.lower()
    
    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)  # ← PyPDF2 usage
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_path}: {e}")
            return ""
    elif ext == ".docx":
        try:
            doc = Document(file_path)
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            return text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX {file_path}: {e}")
            return ""
    return ""

def extract_resume_text_from_minio(object_name: str) -> str:
    """
    Extract text from a file stored in MinIO.
    Downloads to temp file, extracts, then cleans up.
    """
    ext = Path(object_name).suffix.lower()
    temp_path = None
    
    try:
        temp_path = MinIOClient.download_to_temp(object_name)
        
        if ext in [".pdf", ".docx"]:
            return extract_text_from_file_path(temp_path)
        else:
            logger.warning(f"Unsupported extension for extraction: {ext}")
            return ""
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()

def extract_resume_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from file bytes (for in-memory processing)."""
    ext = Path(filename).suffix.lower()
    
    if ext == ".pdf":
        return extract_text_from_pdf_bytes(content)  # ← Uses PyPDF2
    elif ext == ".docx":
        return extract_text_from_docx_bytes(content)
    else:
        logger.warning(f"Unsupported extension for extraction: {ext}")
        return ""