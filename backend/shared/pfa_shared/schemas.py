from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from pfa_shared.enums import ServiceName


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    service: ServiceName
