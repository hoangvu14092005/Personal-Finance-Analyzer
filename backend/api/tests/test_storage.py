"""Unit tests cho storage adapters (M5).

- `LocalStorageService` test trên tmp_path.
- `S3StorageService` test bằng moto/mock — nhưng để tránh thêm dependency,
  ta mock `boto3.client` qua monkeypatch.
- `get_storage_service` factory dispatch theo settings.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from app.core.config import Settings, get_settings
from app.integrations.storage import (
    LocalStorageService,
    S3StorageService,
    StorageNotFoundError,
    get_storage_service,
)
from pfa_shared.enums import AppEnv


class TestLocalStorageService:
    def test_upload_then_download_roundtrip(self, tmp_path: Path) -> None:
        service = LocalStorageService(root_dir=tmp_path)
        content = b"hello receipt"
        result = service.upload_bytes("u1/file.jpg", content, "image/jpeg")

        assert result.storage_key == "u1/file.jpg"
        assert result.size_bytes == len(content)
        assert (tmp_path / "u1" / "file.jpg").read_bytes() == content
        assert service.download_bytes("u1/file.jpg") == content

    def test_download_missing_raises(self, tmp_path: Path) -> None:
        service = LocalStorageService(root_dir=tmp_path)
        with pytest.raises(StorageNotFoundError):
            service.download_bytes("missing.jpg")

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        service = LocalStorageService(root_dir=tmp_path)
        service.upload_bytes("u1/del.jpg", b"x", "image/jpeg")
        service.delete("u1/del.jpg")
        assert not (tmp_path / "u1" / "del.jpg").exists()

    def test_delete_idempotent_when_missing(self, tmp_path: Path) -> None:
        service = LocalStorageService(root_dir=tmp_path)
        # Should not raise.
        service.delete("never.jpg")


class TestS3StorageServiceMocked:
    """Test S3StorageService với boto3 client bị mock toàn bộ.

    Mục đích: verify wiring (params đúng vào put_object/get_object/delete_object)
    + behavior NoSuchKey → StorageNotFoundError. Không spin up MinIO/moto thật.
    """

    @pytest.fixture
    def mock_boto_client(self, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
        # `S3StorageService` lazy import boto3 + botocore.client trong
        # constructor → patch qua sys.modules để intercept import.
        import sys

        client = MagicMock()
        fake_boto3 = MagicMock()
        fake_boto3.client = MagicMock(return_value=client)
        monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

        fake_botocore_client_module = MagicMock()
        fake_botocore_client_module.Config = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(
            sys.modules,
            "botocore.client",
            fake_botocore_client_module,
        )
        return client

    def test_upload_calls_put_object_with_content_type(
        self,
        mock_boto_client: MagicMock,
    ) -> None:
        service = S3StorageService(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="k",
            secret_key="s",
            bucket="receipts",
        )
        result = service.upload_bytes("u1/r.jpg", b"img", "image/jpeg")

        mock_boto_client.put_object.assert_called_once_with(
            Bucket="receipts",
            Key="u1/r.jpg",
            Body=b"img",
            ContentType="image/jpeg",
        )
        assert result.storage_key == "u1/r.jpg"
        assert result.size_bytes == 3

    def test_download_returns_bytes(self, mock_boto_client: MagicMock) -> None:
        body_stream = MagicMock()
        body_stream.read.return_value = b"hello"
        mock_boto_client.get_object.return_value = {"Body": body_stream}

        service = S3StorageService(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="k",
            secret_key="s",
            bucket="receipts",
        )
        result = service.download_bytes("u1/r.jpg")

        mock_boto_client.get_object.assert_called_once_with(
            Bucket="receipts",
            Key="u1/r.jpg",
        )
        body_stream.close.assert_called_once()
        assert result == b"hello"

    def test_download_missing_raises_storage_not_found(
        self,
        mock_boto_client: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Tạo fake ClientError để raise.
        class FakeClientError(Exception):
            def __init__(self, code: str) -> None:
                super().__init__(code)
                self.response = {"Error": {"Code": code}}

        import sys

        fake_botocore_exceptions = MagicMock()
        fake_botocore_exceptions.ClientError = FakeClientError
        monkeypatch.setitem(
            sys.modules,
            "botocore.exceptions",
            fake_botocore_exceptions,
        )

        mock_boto_client.get_object.side_effect = FakeClientError("NoSuchKey")

        service = S3StorageService(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="k",
            secret_key="s",
            bucket="receipts",
        )
        with pytest.raises(StorageNotFoundError):
            service.download_bytes("missing.jpg")

    def test_delete_calls_delete_object(self, mock_boto_client: MagicMock) -> None:
        service = S3StorageService(
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key="k",
            secret_key="s",
            bucket="receipts",
        )
        service.delete("u1/r.jpg")
        mock_boto_client.delete_object.assert_called_once_with(
            Bucket="receipts",
            Key="u1/r.jpg",
        )


class TestStorageFactory:
    def test_factory_returns_local_service_by_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        get_settings.cache_clear()
        monkeypatch.setenv("STORAGE_BACKEND", "local")
        monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
        monkeypatch.setenv("APP_ENV", AppEnv.LOCAL.value)

        service = get_storage_service()
        assert isinstance(service, LocalStorageService)
        assert service.root_dir == tmp_path

        get_settings.cache_clear()

    def test_factory_returns_s3_service_when_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Mock boto3 vì factory sẽ instantiate S3StorageService.
        import sys

        fake_boto3 = MagicMock()
        fake_boto3.client = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
        fake_botocore_client = MagicMock()
        fake_botocore_client.Config = MagicMock(return_value=MagicMock())
        monkeypatch.setitem(sys.modules, "botocore.client", fake_botocore_client)

        get_settings.cache_clear()
        monkeypatch.setenv("STORAGE_BACKEND", "s3")
        monkeypatch.setenv("APP_ENV", AppEnv.LOCAL.value)
        monkeypatch.setenv("S3_ENDPOINT", "http://minio:9000")
        monkeypatch.setenv("S3_BUCKET_PRIVATE", "test-bucket")

        service = get_storage_service()
        assert isinstance(service, S3StorageService)
        assert service.bucket == "test-bucket"

        get_settings.cache_clear()


def test_settings_storage_backend_defaults_to_local() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.storage_backend == "local"
    assert settings.storage_local_root == "data/receipts"
