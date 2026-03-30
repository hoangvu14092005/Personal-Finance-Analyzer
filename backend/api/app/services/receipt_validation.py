from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


def validate_upload_file(
    upload_file: UploadFile,
    file_size_bytes: int,
    max_file_size_mb: int,
) -> None:
    extension = Path(upload_file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension. Allowed: JPG, PNG, PDF.",
        )

    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported MIME type. Allowed: image/jpeg, image/png, application/pdf.",
        )

    max_bytes = max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size is {max_file_size_mb}MB.",
        )
