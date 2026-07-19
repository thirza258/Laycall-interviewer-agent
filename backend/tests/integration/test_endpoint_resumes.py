import pytest
from unittest.mock import patch, AsyncMock

from app.db.models.interview import Interview


class TestResumeUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_resume_requires_existing_interview(self, test_client, db_session):
        """Uploading a resume for a non-existent interview should return 404."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        # Use an invalid interview_id
        with patch("app.api.endpoints.resumes.validate_file") as mock_validate, \
             patch("app.api.endpoints.resumes.upload_to_minio") as mock_upload, \
             patch("app.api.endpoints.resumes.extract_resume_text_from_bytes") as mock_extract:

            mock_validate.return_value = None
            mock_upload.return_value = ("resumes/999/file.pdf", "https://example.com/file.pdf")
            mock_extract.return_value = "Extracted resume text"

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.4 mock content", "application/pdf")},
                data={"interview_id": "99999"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_resume_success(self, test_client, db_session):
        """Uploading a valid resume to an existing interview should return 201."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate, \
             patch("app.api.endpoints.resumes.upload_to_minio") as mock_upload, \
             patch("app.api.endpoints.resumes.extract_resume_text_from_bytes") as mock_extract:

            mock_validate.return_value = None
            mock_upload.return_value = ("resumes/1/abc.pdf", "https://pub.example.com/test-bucket/resumes/1/abc.pdf")
            mock_extract.return_value = "Extracted resume text content"

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.4 mock", "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Resume uploaded successfully"
        assert data["resume"]["interview_id"] == interview.id
        assert data["resume"]["file_path"] == "resumes/1/abc.pdf"
        assert data["resume"]["raw_text"] == "Extracted resume text content"
        assert data["resume"]["id"] is not None

    @pytest.mark.asyncio
    async def test_upload_resume_without_file(self, test_client, db_session):
        """Uploading without a file should return 422 (FastAPI validation)."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        response = await test_client.post(
            "/api/v1/resumes",
            data={"interview_id": str(interview.id)},
        )

        assert response.status_code == 422
