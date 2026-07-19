import logging
import tempfile
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class MinIOClient:
    _instance: Minio | None = None
    
    @classmethod
    def get_client(cls) -> Minio:
        """Get or create the MinIO client instance (singleton pattern)."""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            # Ensure bucket exists
            cls._ensure_bucket_exists(settings.MINIO_BUCKET)
        return cls._instance
    
    @classmethod
    def _ensure_bucket_exists(cls, bucket_name: str) -> None:
        """Create bucket if it doesn't exist."""
        client = cls.get_client()
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
        except S3Error as e:
            logger.error(f"Failed to create MinIO bucket {bucket_name}: {e}")
            raise
    
    @classmethod
    def upload_file(
        cls,
        file_path: str | Path,
        object_name: str,
        bucket: str | None = None,
        content_type: str | None = None
    ) -> str:
        """
        Upload a file to MinIO.
        Returns the public URL of the uploaded object.
        """
        settings = get_settings()
        bucket = bucket or settings.MINIO_BUCKET
        client = cls.get_client()
        
        try:
            client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=str(file_path),
                content_type=content_type
            )
            
            return f"{settings.MINIO_PUBLIC_URL}/{bucket}/{object_name}"
            
        except S3Error as e:
            logger.error(f"Failed to upload {object_name} to MinIO: {e}")
            raise
    
    @classmethod
    def upload_fileobj(
        cls,
        file_obj,
        object_name: str,
        file_size: int,
        bucket: str | None = None,
        content_type: str | None = None
    ) -> str:
        """
        Upload a file-like object to MinIO (for in-memory uploads).
        Returns the public URL of the uploaded object.
        """
        settings = get_settings()
        bucket = bucket or settings.MINIO_BUCKET
        client = cls.get_client()
        
        try:
            client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_obj,
                length=file_size,
                content_type=content_type
            )
            
            return f"{settings.MINIO_PUBLIC_URL}/{bucket}/{object_name}"
            
        except S3Error as e:
            logger.error(f"Failed to upload {object_name} to MinIO: {e}")
            raise
    
    @classmethod
    def download_to_temp(cls, object_name: str, bucket: str | None = None) -> str:
        """
        Download a file from MinIO to a temporary file.
        Returns the path to the temporary file (caller should clean up).
        """
        settings = get_settings()
        bucket = bucket or settings.MINIO_BUCKET
        client = cls.get_client()
        
        # Create temp file with original extension
        ext = Path(object_name).suffix or ".tmp"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            client.fget_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=temp_path
            )
            return temp_path
        except S3Error as e:
            logger.error(f"Failed to download {object_name} from MinIO: {e}")
            Path(temp_path).unlink(missing_ok=True)
            raise
    
    @classmethod
    def get_object_url(cls, object_name: str, bucket: str | None = None) -> str:
        """Generate public URL for an object without uploading."""
        settings = get_settings()
        bucket = bucket or settings.MINIO_BUCKET
        return f"{settings.MINIO_PUBLIC_URL}/{bucket}/{object_name}"