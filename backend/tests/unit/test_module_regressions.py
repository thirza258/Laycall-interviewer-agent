"""Boundary cases that are missed by the happy-path module tests."""

import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from docx import Document
from sqlalchemy.engine import make_url

from app.agents.question_generator import QuestionGeneratorAgent
from app.agents.utils import parse_and_validate_llm_json
from app.core.config import Settings
from app.core.minio_client import MinIOClient
from app.llm.exceptions import OpenRouterValidationError
from app.llm.models import LLMResponse
from app.schemas.agents import FinalInterviewSpec, GeneratedQuestions
from app.services.resume_parser import extract_text_from_docx_bytes, extract_text_from_file_path


def test_database_credentials_round_trip_reserved_characters():
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None, DB_USER="user@example.com", DB_PASSWORD="p@ss/word:%?#")
    parsed = make_url(settings.DATABASE_URL)
    assert parsed.username == settings.DB_USER
    assert parsed.password == settings.DB_PASSWORD
    assert parsed.host == settings.DB_HOST


def test_offline_migrations_accept_percent_encoded_credentials():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        env={**os.environ, "DATABASE_URL": "postgresql+asyncpg://user:p%40ss@localhost/test"},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE interviews" in result.stdout


@pytest.mark.parametrize("from_disk", [False, True])
def test_docx_resume_includes_tables_in_document_order(tmp_path, from_disk):
    document = Document()
    document.add_paragraph("Jane Doe")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Experience"
    cell = table.cell(0, 1)
    cell.text = "Python developer"
    nested = cell.add_table(rows=1, cols=1)
    nested.cell(0, 0).text = "Five years"
    document.add_paragraph("Education")
    stream = io.BytesIO()
    document.save(stream)
    if from_disk:
        path = tmp_path / "resume.docx"
        path.write_bytes(stream.getvalue())
        text = extract_text_from_file_path(str(path))
    else:
        text = extract_text_from_docx_bytes(stream.getvalue())
    assert text.splitlines() == ["Jane Doe", "Experience", "Python developer", "Five years", "Education"]


@pytest.mark.parametrize("questions", [[], [{"question": "   ", "type": "technical", "difficulty": "easy"}]])
async def test_question_generation_rejects_empty_content(fake_llm_client, questions):
    fake_llm_client.generate_completion.return_value = LLMResponse(
        content=json.dumps({"questions": questions}), model="fake/model", finish_reason="stop"
    )
    with pytest.raises(OpenRouterValidationError):
        await QuestionGeneratorAgent(fake_llm_client).generate(
            FinalInterviewSpec(target_role="Developer", difficulty="mid")
        )


def test_missing_llm_content_raises_the_domain_error():
    with pytest.raises(OpenRouterValidationError):
        parse_and_validate_llm_json(None, GeneratedQuestions)


def test_failed_download_removes_temporary_file_for_network_errors():
    client = MagicMock()
    client.fget_object.side_effect = ConnectionError("Storage disconnected")
    with patch.object(MinIOClient, "get_client", return_value=client):
        with pytest.raises(ConnectionError):
            MinIOClient.download_to_temp("resume.pdf")
    path = Path(client.fget_object.call_args.kwargs["file_path"])
    try:
        assert not path.exists()
    finally:
        path.unlink(missing_ok=True)


def test_storage_initialization_retries_after_a_connection_failure():
    settings = MagicMock(MINIO_ENDPOINT="localhost:9000", MINIO_BUCKET="interviews")
    client = MagicMock()
    client.bucket_exists.side_effect = [ConnectionError("Storage starting"), False]
    with patch("app.core.minio_client.get_settings", return_value=settings), \
         patch("app.core.minio_client.Minio", return_value=client):
        with pytest.raises(ConnectionError):
            MinIOClient.get_client()
        assert MinIOClient.get_client() is client
    assert client.bucket_exists.call_count == 2
    client.make_bucket.assert_called_once_with("interviews")
