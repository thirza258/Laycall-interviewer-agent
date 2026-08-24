import io
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.resume_parser import (
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes,
    extract_text_from_file_path,
    extract_resume_text_from_bytes,
    extract_resume_text_from_minio,
)


class TestPdfExtraction:
    def test_extract_returns_empty_on_invalid_bytes(self):
        """Extracting from invalid PDF bytes should return empty string, not crash."""
        result = extract_text_from_pdf_bytes(b"not a valid pdf")
        assert result == ""

    def test_extract_returns_empty_on_empty_bytes(self):
        result = extract_text_from_pdf_bytes(b"")
        assert result == ""

    def test_extract_from_minimal_pdf(self):
        """Extract text from a minimal valid PDF."""
        # Minimal PDF with readable text
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n190\n%%EOF"
        )
        result = extract_text_from_pdf_bytes(pdf_bytes)
        # May return empty for a PDF without actual text content, but shouldn't crash
        assert isinstance(result, str)


class TestDocxExtraction:
    def test_extract_returns_empty_on_invalid_bytes(self):
        """Extracting from invalid DOCX bytes should return empty string, not crash."""
        result = extract_text_from_docx_bytes(b"not a valid docx")
        assert result == ""

    def test_extract_returns_empty_on_empty_bytes(self):
        result = extract_text_from_docx_bytes(b"")
        assert result == ""


class TestExtractResumeTextFromBytes:
    def test_pdf_extension_routes_to_pdf_extractor(self):
        result = extract_resume_text_from_bytes(b"%PDF-1.4\n%%EOF", "resume.pdf")
        assert isinstance(result, str)

    def test_docx_extension_routes_to_docx_extractor(self):
        result = extract_resume_text_from_bytes(b"PK\x03\x04", "resume.docx")
        assert isinstance(result, str)  # Invalid zip, returns ""

    def test_unsupported_extension_returns_empty(self):
        result = extract_resume_text_from_bytes(b"hello", "resume.txt")
        assert result == ""

    def test_no_extension_returns_empty(self):
        result = extract_resume_text_from_bytes(b"hello", "resume")
        assert result == ""


class TestExtractTextFromFilePath:
    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = extract_text_from_file_path(str(f))
        assert result == ""

    def test_nonexistent_file_returns_empty(self):
        result = extract_text_from_file_path("/nonexistent/path/file.pdf")
        assert result == ""


def _write_docx(path: Path, text: str) -> Path:
    from docx import Document

    document = Document()
    document.add_paragraph(text)
    document.save(path)
    return path


class TestExtractFromMinio:
    def test_extracts_text_from_the_downloaded_copy(self, tmp_path):
        local = _write_docx(tmp_path / "cv.docx", "Ada Lovelace — Engineer")

        with patch(
            "app.services.resume_parser.MinIOClient.download_to_temp",
            return_value=str(local),
        ) as download:
            text = extract_resume_text_from_minio("resumes/1/cv.docx")

        download.assert_called_once_with("resumes/1/cv.docx")
        assert "Ada Lovelace" in text

    def test_removes_the_downloaded_copy(self, tmp_path):
        local = _write_docx(tmp_path / "cv.docx", "Some text")

        with patch(
            "app.services.resume_parser.MinIOClient.download_to_temp",
            return_value=str(local),
        ):
            extract_resume_text_from_minio("resumes/1/cv.docx")

        assert not local.exists()

    def test_unsupported_extension_skips_extraction(self, tmp_path):
        local = tmp_path / "cv.txt"
        local.write_text("plain text resume")

        with patch(
            "app.services.resume_parser.MinIOClient.download_to_temp",
            return_value=str(local),
        ):
            assert extract_resume_text_from_minio("resumes/1/cv.txt") == ""

    def test_cleans_up_when_extraction_raises(self, tmp_path):
        local = _write_docx(tmp_path / "cv.docx", "text")

        with patch(
            "app.services.resume_parser.MinIOClient.download_to_temp",
            return_value=str(local),
        ), patch(
            "app.services.resume_parser.extract_text_from_file_path",
            side_effect=RuntimeError("parser crashed"),
        ):
            with pytest.raises(RuntimeError):
                extract_resume_text_from_minio("resumes/1/cv.docx")

        assert not local.exists()
