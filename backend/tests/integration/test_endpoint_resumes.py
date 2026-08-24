import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

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


class TestResumeUploadEdgeCases:
    @pytest.mark.asyncio
    async def test_upload_resume_empty_file(self, test_client, db_session):
        """Uploading an empty file should return 400."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate:
            mock_validate.return_value = None

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("empty.pdf", b"", "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_resume_invalid_file_type(self, test_client, db_session):
        """Uploading a file with an invalid extension should return 400."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate:
            mock_validate.side_effect = HTTPException(
                status_code=400,
                detail="Invalid file type. Allowed types: .pdf, .docx"
            )

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.exe", b"malicious", "application/octet-stream")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_resume_file_too_large(self, test_client, db_session):
        """Uploading a file exceeding the size limit should return 400."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate:
            mock_validate.side_effect = HTTPException(
                status_code=400,
                detail="File size exceeds the maximum allowed size of 10 MB"
            )

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("large.pdf", b"x" * 100, "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 400
        assert "File size" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_resume_file_read_failure(self, test_client, db_session):
        """Failure to read the uploaded file should return 500."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        # The multipart parser hands the endpoint a starlette UploadFile, so
        # patching fastapi's subclass leaves read() working and the 500 comes
        # from storage instead — a pass for the wrong reason.
        with patch("app.api.endpoints.resumes.validate_file") as mock_validate, \
             patch("app.api.endpoints.resumes.upload_to_minio") as mock_upload, \
             patch(
                 "starlette.datastructures.UploadFile.read", new_callable=AsyncMock
             ) as mock_read:

            mock_validate.return_value = None
            mock_read.side_effect = Exception("Simulated read failure")

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.4 content", "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to process uploaded file"
        mock_upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_upload_resume_minio_failure(self, test_client, db_session):
        """MinIO upload failure should return 500."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate, \
             patch("app.api.endpoints.resumes.upload_to_minio") as mock_upload:

            mock_validate.return_value = None
            mock_upload.side_effect = Exception("MinIO connection refused")

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.4 content", "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_upload_resume_missing_interview_id(self, test_client, db_session):
        """Uploading without an interview_id should return 422."""
        response = await test_client.post(
            "/api/v1/resumes",
            files={"file": ("resume.pdf", b"content", "application/pdf")},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_resume_question_generation_failure(self, test_client, db_session):
        """Resume upload should succeed even if question generation fails."""
        interview = Interview()
        db_session.add(interview)
        await db_session.commit()

        with patch("app.api.endpoints.resumes.validate_file") as mock_validate, \
             patch("app.api.endpoints.resumes.upload_to_minio") as mock_upload, \
             patch("app.api.endpoints.resumes.extract_resume_text_from_bytes") as mock_extract, \
             patch("app.api.endpoints.resumes.InterviewOrchestrationService") as mock_orch:

            mock_validate.return_value = None
            mock_upload.return_value = ("resumes/1/file.pdf", "https://example.com/file.pdf")
            mock_extract.return_value = "Extracted text"

            mock_orch_instance = mock_orch.return_value
            mock_orch_instance.generate_questions = AsyncMock(
                side_effect=Exception("LLM error during question generation")
            )

            response = await test_client.post(
                "/api/v1/resumes",
                files={"file": ("resume.pdf", b"%PDF-1.4 mock", "application/pdf")},
                data={"interview_id": str(interview.id)},
            )

        # Upload should still succeed even if question generation fails
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Resume uploaded successfully"
