"""S3StorageService — adapter cho MinIO/AWS S3.

Dùng boto3 với endpoint_url (hỗ trợ MinIO local + AWS S3 thật). boto3 import
lazy trong constructor — code path local backend không cần boto3 cài đặt
(dù shared không khai báo boto3 dep, host package API/worker đều add boto3).
"""
from __future__ import annotations

from typing import Any

from pfa_shared.storage.base import (
    StorageNotFoundError,
    StorageService,
    StoredObject,
)


class S3StorageService(StorageService):
    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        # Lazy import — package shared không declare boto3 dep, nhưng host
        # package (API hoặc worker) phải cài boto3 nếu dùng s3 backend.
        import boto3
        from botocore.client import Config

        self.bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                retries={"max_attempts": 2},
                signature_version="s3v4",
            ),
        )

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str) -> StoredObject:
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": storage_key,
            "Body": content,
        }
        if content_type:
            kwargs["ContentType"] = content_type
        self._client.put_object(**kwargs)
        return StoredObject(storage_key=storage_key, size_bytes=len(content))

    def download_bytes(self, storage_key: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            response = self._client.get_object(Bucket=self.bucket, Key=storage_key)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in {"NoSuchKey", "404"}:
                raise StorageNotFoundError(
                    f"storage_key not found: {storage_key}",
                ) from exc
            raise
        body = response["Body"]
        try:
            return bytes(body.read())
        finally:
            body.close()

    def delete(self, storage_key: str) -> None:
        # S3 delete idempotent — không raise nếu key không tồn tại.
        self._client.delete_object(Bucket=self.bucket, Key=storage_key)
