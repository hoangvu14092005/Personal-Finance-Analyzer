"""Data export/privacy APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import User
from app.schemas.data_exports import DataExportCreate, DataExportResponse
from app.services.audit import record_audit_event
from app.services.data_exports import create_data_export, get_data_export

router = APIRouter(prefix="/data", tags=["data"])


def _require_user_id(current_user: User) -> int:
    if current_user.id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return current_user.id


@router.post("/export", response_model=DataExportResponse, status_code=status.HTTP_202_ACCEPTED)
def post_data_export(
    payload: DataExportCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DataExportResponse:
    user_id = _require_user_id(current_user)
    response = create_data_export(user_id, payload)
    record_audit_event(
        session,
        user_id=user_id,
        event="data.export_requested",
        target_type="data_export",
        target_id=response.export_id,
        metadata={"included": ",".join(response.included)},
        commit=True,
    )
    return response


@router.get("/export/{export_id}", response_model=DataExportResponse)
def get_data_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user),
) -> DataExportResponse:
    user_id = _require_user_id(current_user)
    response = get_data_export(user_id, export_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    return response


@router.delete("/receipt-files", status_code=status.HTTP_409_CONFLICT)
def delete_receipt_files(current_user: User = Depends(get_current_user)) -> None:
    _require_user_id(current_user)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Bulk receipt file deletion requires a retention job and is not enabled yet",
    )


__all__ = ["router"]
