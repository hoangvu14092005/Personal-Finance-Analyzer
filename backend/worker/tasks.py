from __future__ import annotations

from worker_app import broker


def build_ping_response() -> str:
    return "ping"


@broker.task
async def ping_task() -> str:
    return build_ping_response()
