"""TaskIQ proxy wrapper cho insight generation (Phase 6.7).

MVP dùng MockInsightProvider chạy sync (<10ms), nên endpoint POST
`/insights/generate` xử lý đồng bộ luôn. Khi user chuyển sang Ollama
hoặc Gemini (latency cao 2-30s), endpoint có thể switch sang enqueue
job qua hàm `enqueue_insight_job` này, polling `GET /insights/latest`
để lấy snapshot khi worker xong.

Mirror pattern `services.ocr_queue`:
- `get_insight_broker()`: TaskIQ broker singleton (cùng Redis URL).
- `enqueue_insight_job(user_id, range_preset, ...)`: push job, fail-soft.
- Worker process consume queue + execute `generate_insight_for_user`.

Worker side chưa được implement (chỉ proxy task body NotImplementedError).
Sẽ được hoàn thiện ở phase Hardening hoặc khi enable LLM provider thật.
"""
from __future__ import annotations

from functools import lru_cache

from pfa_shared.config import CommonSettings
from taskiq import AsyncBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.logging import get_logger

logger = get_logger("api.insights.queue")

INSIGHT_TASK_NAME = "tasks:generate_insight_job"


@lru_cache(maxsize=1)
def get_insight_broker() -> AsyncBroker:
    """Build broker singleton + register proxy task name.

    Worker process sẽ override task body với implementation thật khi
    Ollama/Gemini được kích hoạt. Proxy ở API chỉ cần tên + signature
    để `kiq()` push job.
    """
    settings = CommonSettings.from_env()
    broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
        RedisAsyncResultBackend(redis_url=settings.redis_url),
    )

    @broker.task(task_name=INSIGHT_TASK_NAME)
    async def _generate_insight_proxy(  # noqa: ARG001
        user_id: int,
        range_preset: str,
        start_date: str | None = None,
        end_date: str | None = None,
        force: bool = False,
    ) -> str:
        raise NotImplementedError(
            "generate_insight_job is consumed by worker process, not API.",
        )

    return broker


async def enqueue_insight_job(
    user_id: int,
    range_preset: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    force: bool = False,
) -> bool:
    """Push insight generation job vào Redis queue. Fail-soft.

    Returns:
        True nếu enqueue OK, False nếu Redis down hoặc task chưa register.
    """
    broker = get_insight_broker()
    task = broker.find_task(INSIGHT_TASK_NAME)
    if task is None:
        logger.error(
            "insight_queue.task_not_registered name=%s user_id=%s",
            INSIGHT_TASK_NAME,
            user_id,
        )
        return False
    try:
        await task.kiq(
            user_id,
            range_preset,
            start_date,
            end_date,
            force,
        )
    except Exception:
        logger.exception(
            "insight_queue.enqueue_failed user_id=%s range=%s",
            user_id,
            range_preset,
        )
        return False
    logger.info(
        "insight_queue.enqueue_ok user_id=%s range=%s force=%s",
        user_id,
        range_preset,
        force,
    )
    return True


__all__ = [
    "INSIGHT_TASK_NAME",
    "enqueue_insight_job",
    "get_insight_broker",
]
