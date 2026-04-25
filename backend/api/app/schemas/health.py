"""Schemas cho readiness/liveness endpoints (M5)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ComponentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: Literal["ok", "down"]
    error: str | None = None


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    components: list[ComponentStatus]
