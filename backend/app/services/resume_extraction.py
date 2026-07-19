import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models.resume import Resume
from app.core.minio_client import MinIOClient
from app.services.resume_parser import extract_text_from_file_path

logger = logging.getLogger(__name__)

class ResumeExtractionService:
    """Service to extract and persist raw text from MinIO-stored resumes."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def extract_and_save(self, resume_id: int) -> str:
        """
        Downloads resume from MinIO, extracts text, and updates resumes.raw_text.
        Returns the extracted raw text.
        """
        # 1. Fetch resume record
        result = await self.db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        
        if not resume:
            raise ValueError(f"Resume with ID {resume_id} not found")
            
        if resume.file_path is None:
            raise ValueError(f"Resume {resume_id} has no associated file path")

        # 2. Download from MinIO to temporary file
        temp_path = MinIOClient.download_to_temp(resume.file_path)
        
        try:
            # 3. Extract text
            raw_text = extract_text_from_file_path(temp_path)
            
            if not raw_text:
                logger.warning(f"No text could be extracted from resume {resume_id}")
                return ""

            # 4. Update database
            await self.db.execute(
                update(Resume)
                .where(Resume.id == resume_id)
                .values(raw_text=raw_text)
            )
            await self.db.commit()
            
            logger.info(f"Successfully extracted and saved text for resume {resume_id}")
            return raw_text
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to extract text for resume {resume_id}: {e}")
            raise
        finally:
            # 5. Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)