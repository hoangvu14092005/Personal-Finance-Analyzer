from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIdMiddleware

settings = get_settings()
configure_logging()

app = FastAPI(
    title="Personal Finance Analyzer API",
    version="0.1.0",
)

app.add_middleware(RequestIdMiddleware)
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
