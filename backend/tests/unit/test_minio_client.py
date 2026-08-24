import tempfile
from pathlib import Path

import pytest
from minio.error import S3Error
from unittest.mock import patch, MagicMock

from app.core.minio_client import MinIOClient


class TestMinIOClient:
    def setup_method(self):
        """Reset the singleton before each test."""
        MinIOClient._instance = None

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_get_client_creates_instance(self, mock_settings, mock_minio_cls):
        """First call to get_client should create a new Minio instance."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        client = MinIOClient.get_client()

        assert client is mock_minio_instance
        mock_minio_cls.assert_called_once_with(
            endpoint="localhost:9000",
            access_key="access",
            secret_key="secret",
            secure=False,
        )

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_get_client_is_singleton(self, mock_settings, mock_minio_cls):
        """Second call should return the cached instance."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        c1 = MinIOClient.get_client()
        c2 = MinIOClient.get_client()

        assert c1 is c2
        assert mock_minio_cls.call_count == 1

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_get_client_creates_bucket_if_missing(self, mock_settings, mock_minio_cls):
        """If the bucket doesn't exist, it should be created."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = False
        mock_minio_cls.return_value = mock_minio_instance

        MinIOClient.get_client()

        mock_minio_instance.make_bucket.assert_called_once_with("test-bucket")

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_upload_fileobj(self, mock_settings, mock_minio_cls):
        """upload_fileobj should call put_object and return a public URL."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
            MINIO_PUBLIC_URL="https://pub.example.com",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        file_obj = MagicMock()
        url = MinIOClient.upload_fileobj(
            file_obj=file_obj,
            object_name="resumes/1/abc.pdf",
            file_size=1024,
            content_type="application/pdf",
        )

        mock_minio_instance.put_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="resumes/1/abc.pdf",
            data=file_obj,
            length=1024,
            content_type="application/pdf",
        )
        assert url == "https://pub.example.com/test-bucket/resumes/1/abc.pdf"

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_upload_file(self, mock_settings, mock_minio_cls, tmp_path):
        """upload_file should call fput_object and return a public URL."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
            MINIO_PUBLIC_URL="https://pub.example.com",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"pdf content")

        url = MinIOClient.upload_file(
            file_path=str(test_file),
            object_name="resumes/1/test.pdf",
        )

        mock_minio_instance.fput_object.assert_called_once()
        assert "https://pub.example.com/test-bucket/resumes/1/test.pdf" == url

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_get_object_url(self, mock_settings, mock_minio_cls):
        """get_object_url should return the constructed public URL."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
            MINIO_PUBLIC_URL="https://pub.example.com",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        url = MinIOClient.get_object_url("path/to/file.pdf")
        assert url == "https://pub.example.com/test-bucket/path/to/file.pdf"

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_get_object_url_custom_bucket(self, mock_settings, mock_minio_cls):
        """get_object_url should accept a custom bucket."""
        mock_settings.return_value = MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="default-bucket",
            MINIO_PUBLIC_URL="https://pub.example.com",
        )
        mock_minio_instance = MagicMock()
        mock_minio_instance.bucket_exists.return_value = True
        mock_minio_cls.return_value = mock_minio_instance

        url = MinIOClient.get_object_url("file.pdf", bucket="custom-bucket")
        assert url == "https://pub.example.com/custom-bucket/file.pdf"


class TestMinIOClientConfiguration:
    def setup_method(self):
        MinIOClient._instance = None

    @patch("app.core.minio_client.get_settings")
    def test_missing_endpoint_names_the_problem(self, mock_settings):
        """Without this guard the minio SDK fails deep inside on endpoint=None."""
        mock_settings.return_value = MagicMock(MINIO_ENDPOINT=None)

        with pytest.raises(RuntimeError, match="Object storage is not configured"):
            MinIOClient.get_client()

    @patch("app.core.minio_client.get_settings")
    def test_empty_endpoint_is_also_rejected(self, mock_settings):
        mock_settings.return_value = MagicMock(MINIO_ENDPOINT="")

        with pytest.raises(RuntimeError):
            MinIOClient.get_client()


class TestDownloadToTemp:
    def setup_method(self):
        MinIOClient._instance = None

    @staticmethod
    def _settings():
        return MagicMock(
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="access",
            MINIO_SECRET_KEY="secret",
            MINIO_SECURE=False,
            MINIO_BUCKET="test-bucket",
            MINIO_PUBLIC_URL="http://localhost:9000",
        )

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_downloads_to_a_temp_file_keeping_the_extension(self, mock_settings, mock_minio_cls):
        mock_settings.return_value = self._settings()
        minio = MagicMock()
        minio.bucket_exists.return_value = True
        mock_minio_cls.return_value = minio

        path = MinIOClient.download_to_temp("resumes/1/cv.pdf")

        assert path.endswith(".pdf")
        minio.fget_object.assert_called_once_with(
            bucket_name="test-bucket", object_name="resumes/1/cv.pdf", file_path=path
        )
        Path(path).unlink(missing_ok=True)

    @patch("app.core.minio_client.Minio")
    @patch("app.core.minio_client.get_settings")
    def test_failed_download_removes_the_temp_file(self, mock_settings, mock_minio_cls):
        """A leaked temp file per failed download would fill the disk."""
        mock_settings.return_value = self._settings()
        minio = MagicMock()
        minio.bucket_exists.return_value = True
        minio.fget_object.side_effect = S3Error(
            "NoSuchKey", "missing", "resource", "req-1", "host-1", None
        )
        mock_minio_cls.return_value = minio

        created = []
        real_named_temp_file = tempfile.NamedTemporaryFile

        def tracking_temp_file(*args, **kwargs):
            handle = real_named_temp_file(*args, **kwargs)
            created.append(handle.name)
            return handle

        with patch("app.core.minio_client.tempfile.NamedTemporaryFile", tracking_temp_file):
            with pytest.raises(S3Error):
                MinIOClient.download_to_temp("resumes/1/missing.pdf")

        assert created and not Path(created[0]).exists()
