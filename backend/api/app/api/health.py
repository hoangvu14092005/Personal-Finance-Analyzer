from fastapi import APIRouter
from pfa_shared.enums import ServiceName
from pfa_shared.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", name="health")
def health_check() -> HealthResponse:
    return HealthResponse(service=ServiceName.API)
