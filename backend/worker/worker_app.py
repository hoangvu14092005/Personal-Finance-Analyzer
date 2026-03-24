from __future__ import annotations

from pfa_shared.config import CommonSettings
from pfa_shared.logging import get_logger
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

settings = CommonSettings.from_env()
logger = get_logger("worker", level=settings.log_level)
logger.info("Initializing worker broker")

broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
    RedisAsyncResultBackend(redis_url=settings.redis_url),
)

