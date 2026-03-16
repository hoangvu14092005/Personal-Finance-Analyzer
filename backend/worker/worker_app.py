from __future__ import annotations

import os

from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

broker = ListQueueBroker(url=REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(redis_url=REDIS_URL),
)

# Import task module for side effects so tasks are registered on startup.
import tasks  # noqa: E402,F401
