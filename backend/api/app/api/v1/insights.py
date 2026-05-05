"""AI Insights API (Phase 6.9).

Endpoints:
- `POST /api/v1/insights/generate`: tính insight mới (hoặc trả cache).
- `GET /api/v1/insights/latest`: trả snapshot mới nhất của (user, preset).

Response shape: `InsightResponse` (schema). Khi không đủ điều kiện hoặc
provider fail → vẫn 200 với `status=insufficient_data` hoặc `"failed"`,
UI hiển thị fallback thay vì throw error.

Error mapping:
- 400: range preset invalid, custom thiếu dates.
- 401: chưa auth (dependency enforce).
- 404: GET /latest không có snapshot nào.
"""
from __future__ import annotations

from datetime import date
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.dependencies.auth import get_current_user
from app.models.entities import InsightSnapshot, User
from app.schemas.insights import (
    GenerateInsightRequest,
    InsightRangeInfo,
    InsightResponse,
    InsightStatus,
)
from app.services.date_ranges import InvalidDateRangeError
from app.services.insights.generator import (
    find_latest_snapshot,
    generate_insight_for_user,
    snapshot_generated_at,
    snapshot_to_payload,
)
from app.services.insights.providers import get_insight_provider

router = APIRouter(prefix="/insights", tags=["insights"])


def _build_response_from_snapshot(
    snapshot: InsightSnapshot,
    *,
    cached: bool,
) -> InsightResponse:
    """Build InsightResponse từ InsightSnapshot entity.

    Dùng khi GET /latest hoặc POST /generate cache hit.
    """
    payload = snapshot_to_payload(snapshot)
    return InsightResponse(
        id=snapshot.id,
        range=InsightRangeInfo(
            preset=snapshot.range_preset,
            start=snapshot.range_start,
            end=snapshot.range_end,
        ),
        status=cast(InsightStatus, snapshot.status),
        status_reason=snapshot.status_reason,
        provider=snapshot.provider,
        fingerprint=snapshot.fingerprint,
        payload=payload,
        generated_at=snapshot_generated_at(snapshot),
        cached=cached,
    )


@router.post(
    "/generate",
    response_model=InsightResponse,
    name="generate_insight",
)
def generate_insight(
    request: GenerateInsightRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InsightResponse:
    """Sinh insight mới cho user.

    Body (optional):
    - `range`: preset key — "7d"/"30d"/"this_month"/"last_month"/"custom".
    - `start_date`/`end_date`: required khi range=custom.
    - `force`: bỏ qua cache, luôn gọi provider (mặc định `false`).

    Behavior:
    1. Tính SummaryInput → fingerprint.
    2. Nếu `force=false` + có snapshot `status=ready` với cùng fingerprint
       → trả cached.
    3. Nếu không eligible → persist snapshot `insufficient_data`, trả
       `status=insufficient_data` + `status_reason`.
    4. Nếu provider lỗi → persist snapshot `failed`, trả
       `status=failed`.
    5. Nếu thành công → persist snapshot `ready`, trả đầy đủ payload.
    """
    # FastAPI optional Body: nếu client không gửi → default request.
    req = request or GenerateInsightRequest()

    try:
        provider = get_insight_provider(settings)
    except Exception as exc:  # provider factory error (vd. gemini thiếu key).
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Insight provider chưa sẵn sàng: {exc}",
        ) from exc

    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User chưa có id (phiên không hợp lệ).",
        )

    try:
        result = generate_insight_for_user(
            session,
            provider,
            current_user.id,
            req,
        )
    except InvalidDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return InsightResponse(
        id=result.snapshot.id,
        range=InsightRangeInfo(
            preset=result.snapshot.range_preset,
            start=result.range_.start,
            end=result.range_.end,
        ),
        status=result.status,
        status_reason=result.status_reason,
        provider=result.snapshot.provider,
        fingerprint=result.fingerprint,
        payload=result.payload,
        generated_at=snapshot_generated_at(result.snapshot),
        cached=result.cached,
    )


@router.get(
    "/latest",
    response_model=InsightResponse,
    name="latest_insight",
)
def get_latest_insight(
    range: str = Query(  # noqa: A002
        "30d",
        description="Range preset — 7d | 30d | this_month | last_month | custom",
    ),
    _start_date: date | None = Query(None, alias="start_date"),
    _end_date: date | None = Query(None, alias="end_date"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InsightResponse:
    """Trả snapshot mới nhất của (user, range_preset).

    Note:
    - `start_date`/`end_date` chỉ dùng khi client dự định generate next;
      endpoint này chỉ filter theo `range_preset` để đơn giản. Nếu cần
      filter theo exact range, client gọi POST /generate thay vì GET.
    - 404 khi chưa có snapshot — UI cần gọi POST /generate trước.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User chưa có id (phiên không hợp lệ).",
        )

    snapshot = find_latest_snapshot(session, current_user.id, range)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có insight nào cho range={range}.",
        )

    return _build_response_from_snapshot(snapshot, cached=True)
