from __future__ import annotations

from worker_app import broker


@broker.task
async def ping_task() -> str:
    return "ping"
