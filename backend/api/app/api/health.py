"""Health & readiness endpoints (M5).

- `/health` & `/health/live`: liveness — chỉ check process còn alive (không
  phụ thuộc DB/Redis/S3). Dùng cho Kubernetes liveness probe.
- `/health/ready`: readiness — deep check DB + Redis + S3 (nếu enabled).
  Trả 200 khi tất cả OK, 503 khi có component down. Dùng cho K8s readiness
  probe và LB health check.
"""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from pfa_shared.enums import ServiceName
from pfa_shared.schemas import HealthResponse

from app.core.config import get_settings
from app.schemas.health import ComponentStatus, ReadinessResponse
from app.services.health_checks import run_readiness_checks

router = APIRouter(tags=["health"])


@router.get("/health", name="health")
def health_check() -> HealthResponse:
    """Liveness probe — backwards compat với `/health` cũ."""
    return HealthResponse(service=ServiceName.API)


@router.get("/health/live", name="health_live")
def health_live() -> HealthResponse:
    """Liveness probe — alias rõ nghĩa cho `/health`."""
    return HealthResponse(service=ServiceName.API)


@router.get(
    "/health/ready",
    name="health_ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_200_OK: {"model": ReadinessResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse},
    },
)
async def health_ready(response: Response) -> ReadinessResponse:
    """Readiness probe — ping DB + Redis + (S3 nếu enabled).

    Status code:
    - 200 OK: tất cả components đều ok → app sẵn sàng nhận traffic.
    - 503 Service Unavailable: có ít nhất 1 component down → LB nên loại
      pod này khỏi rotation.

    Body luôn trả `ReadinessResponse` (kể cả 503) để monitoring phân biệt
    component nào fail.
    """
    settings = get_settings()
    results = await run_readiness_checks(settings)
    components = [
        ComponentStatus(
            name=result.name,
            status="ok" if result.ok else "down",
            error=result.error,
        )
        for result in results
    ]
    overall_ok = all(result.ok for result in results)
    if not overall_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if overall_ok else "degraded",
        components=components,
    )
