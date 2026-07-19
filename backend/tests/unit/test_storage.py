import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.storage.storage import (
    validate_file,
    generate_object_name,
    upload_to_minio,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)


class TestValidateFile:
    def test_valid_pdf_passes(self):
        validate_file("resume.pdf", 1024, "application/pdf")

    def test_valid_docx_passes(self):
        validate_file("resume.docx", 1024, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_invalid_extension_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_file("resume.txt", 1024, "text/plain")
        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    def test_file_too_large_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_file("resume.pdf", MAX_FILE_SIZE + 1, "application/pdf")
        assert exc_info.value.status_code == 400
        assert "too large" in exc_info.value.detail

    def test_file_size_none_passes(self):
        """None size should be allowed (e.g. when size is unknown)."""
        validate_file("resume.pdf", None, "application/pdf")

    def test_file_at_max_size_passes(self):
        validate_file("resume.pdf", MAX_FILE_SIZE, "application/pdf")

    def test_extension_case_insensitive(self):
        validate_file("RESUME.PDF", 1024, None)
        validate_file("Resume.Docx", 1024, None)

    def test_no_extension_raises(self):
        with pytest.raises(HTTPException):
            validate_file("resume", 1024, None)


class TestGenerateObjectName:
    def test_generates_unique_path(self):
        name = generate_object_name(42, "resume.pdf")
        assert name.startswith("resumes/42/")
        assert name.endswith(".pdf")

    def test_generates_different_names_for_same_input(self):
        """Each call should produce a unique name (UUID)."""
        name1 = generate_object_name(1, "file.pdf")
        name2 = generate_object_name(1, "file.pdf")
        assert name1 != name2

    def test_handles_docx_extension(self):
        name = generate_object_name(1, "cv.docx")
        assert name.endswith(".docx")


class TestUploadToMinio:
    @patch("app.storage.storage.MinIOClient.upload_fileobj")
    @patch("app.storage.storage.validate_file")
    def test_upload_returns_object_name_and_url(self, mock_validate, mock_upload, monkeypatch):
        mock_upload.return_value = "https://minio.example.com/bucket/object.pdf"

        object_name, public_url = upload_to_minio(
            b"fake pdf bytes",
            "resume.pdf",
            interview_id=1,
            content_type="application/pdf",
        )

        assert "resumes/1/" in object_name
        assert object_name.endswith(".pdf")
        assert public_url == "https://minio.example.com/bucket/object.pdf"
        mock_validate.assert_called_once()
        mock_upload.assert_called_once()

    @patch("app.storage.storage.MinIOClient.upload_fileobj")
    @patch("app.storage.storage.validate_file")
    def test_upload_validates_before_upload(self, mock_validate, mock_upload, monkeypatch):
        mock_validate.side_effect = HTTPException(status_code=400, detail="Invalid")

        with pytest.raises(HTTPException):
            upload_to_minio(b"data", "bad.txt", interview_id=1)

        mock_validate.assert_called_once()
        mock_upload.assert_not_called()

    @patch("app.storage.storage.MinIOClient.upload_fileobj")
    @patch("app.storage.storage.validate_file")
    def test_upload_auto_detects_content_type(self, mock_validate, mock_upload, monkeypatch):
        """When content_type is not provided, it should be guessed from extension."""
        mock_upload.return_value = "https://example.com/b/file.pdf"

        _, _ = upload_to_minio(b"%PDF-1.4\n", "resume.pdf", interview_id=1)

        call_kwargs = mock_upload.call_args.kwargs
        assert call_kwargs["content_type"] == "application/pdf"
