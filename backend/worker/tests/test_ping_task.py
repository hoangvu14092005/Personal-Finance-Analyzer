from __future__ import annotations

from tasks import build_ping_response


def test_ping_task_returns_ping() -> None:
    assert build_ping_response() == "ping"
