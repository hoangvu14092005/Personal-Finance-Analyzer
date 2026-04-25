"""Service `ocr_queue` — producer phía API push OCR job vào TaskIQ Redis queue.

Thiết kế:
- Reuse cùng broker config (Redis URL) với worker thông qua `pfa_shared.config`.
- Đăng ký một "proxy task" cùng tên với task của worker (`tasks:process_ocr_job`)
  để API có thể dispatch qua kicker tiêu chuẩn của TaskIQ. Body của proxy task
  chỉ raise vì execution thực do worker đảm nhiệm.
- KHÔNG còn `sys.path.insert` (anti-pattern import worker code từ API).
- Lỗi enqueue được log đầy đủ thay vì swallow im lặng.
"""
from __future__ import annotations

from functools import lru_cache

from pfa_shared.config import CommonSettings
from taskiq import AsyncBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.logging import get_logger

logger = get_logger("api.ocr_queue")

# Tên task phải khớp với task worker decorate trong `backend/worker/tasks.py`.
# TaskIQ default task_name = f"{module_name}:{func_name}".
OCR_TASK_NAME = "tasks:process_ocr_job"


@lru_cache(maxsize=1)
def get_ocr_broker() -> AsyncBroker:
    """Build broker singleton dùng cùng Redis với worker.

    Đăng ký proxy task với cùng `task_name` như worker để API có thể dispatch
    qua kicker tiêu chuẩn. Body chỉ raise vì execution thực do worker xử lý.
    """
    settings = CommonSettings.from_env()
    broker = ListQueueBroker(url=settings.redis_url).with_result_backend(
        RedisAsyncResultBackend(redis_url=settings.redis_url),
    )

    @broker.task(task_name=OCR_TASK_NAME)
    async def _process_ocr_job_proxy(receipt_id: int) -> str:  # noqa: ARG001
        raise NotImplementedError(
            "process_ocr_job is consumed by the worker process, not the API",
        )

    return broker


async def enqueue_ocr_job(receipt_id: int) -> bool:
    """Đẩy OCR job vào queue Redis cho worker xử lý.

    Returns:
        True khi enqueue thành công.
        False khi fail (đã log lỗi đầy đủ kèm `receipt_id` để truy vết).
    """
    broker = get_ocr_broker()
    task = broker.find_task(OCR_TASK_NAME)
    if task is None:
        logger.error(
            "ocr_queue.task_not_registered name=%s receipt_id=%s",
            OCR_TASK_NAME,
            receipt_id,
        )
        return False

    try:
        await task.kiq(receipt_id)
    except Exception:
        logger.exception(
            "ocr_queue.enqueue_failed receipt_id=%s task=%s",
            receipt_id,
            OCR_TASK_NAME,
        )
        return False

    logger.info(
        "ocr_queue.enqueue_success receipt_id=%s task=%s",
        receipt_id,
        OCR_TASK_NAME,
    )
    return True
