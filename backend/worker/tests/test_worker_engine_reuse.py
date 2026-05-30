"""Bug 5 — Worker dùng engine module-level dùng chung (không leak pool).

Fix check:
- `worker_app.engine` tồn tại như một singleton phạm vi process.
- `tasks` và `index_tasks` tham chiếu cùng object engine đó.
- Thân task KHÔNG gọi `create_engine` (đã bỏ import nội bộ).
"""
from __future__ import annotations

from sqlalchemy.engine import Engine

import index_tasks
import tasks
import worker_app


def test_worker_app_exposes_shared_engine() -> None:
    assert isinstance(worker_app.engine, Engine)


def test_tasks_use_shared_engine_instance() -> None:
    # Cả hai module import cùng một engine object từ worker_app.
    assert tasks.engine is worker_app.engine
    assert index_tasks.engine is worker_app.engine


def test_task_modules_do_not_import_create_engine() -> None:
    # create_engine không còn được bind ở module task (tránh tạo engine/pool mới).
    assert not hasattr(tasks, "create_engine")
    assert not hasattr(index_tasks, "create_engine")


def test_engine_has_pool_pre_ping_recycle() -> None:
    # Cấu hình cho long-lived worker: pre-ping + recycle.
    assert worker_app.engine.pool._pre_ping is True
    assert worker_app.engine.pool._recycle == 1800
