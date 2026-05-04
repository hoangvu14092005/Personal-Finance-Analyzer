"""OCR queue service: API push jobs vào Redis queue cho worker.

M5 changes:
- Broker startup/shutdown qua FastAPI lifespan (không lazy connect)
- Proxy task để API dispatch qua TaskIQ kicker chuẩn
- Fail-soft: Redis down → enqueue trả False, endpoint rollback sang UPLOADED

Flow:
1. API startup → startup_ocr_broker() connect Redis
2. Upload endpoint → enqueue_ocr_job(receipt_id) push job
3. Worker consume job từ Redis queue
4. API shutdown → shutdown_ocr_broker() cleanup
"""
from __future__ import annotations

from functools import lru_cache

from pfa_shared.config import CommonSettings
from taskiq import AsyncBroker
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.logging import get_logger

logger = get_logger("api.ocr_queue")

# Task name phải khớp với worker task: "tasks:process_ocr_job"
OCR_TASK_NAME = "tasks:process_ocr_job"


@lru_cache(maxsize=1)
def get_ocr_broker() -> AsyncBroker:
    """Build broker singleton với proxy task.
    
    Proxy task body chỉ raise vì execution thực do worker xử lý.
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


async def startup_ocr_broker() -> bool:
    """Khởi tạo broker khi API startup (gọi từ FastAPI lifespan).
    
    Returns:
        True nếu OK, False nếu Redis down.
        API vẫn chạy được khi False - enqueue sẽ fail-soft.
    """
    try:
        broker = get_ocr_broker()
        await broker.startup()
    except Exception:
        logger.exception("ocr_queue.startup_failed")
        return False
    logger.info("ocr_queue.startup_ok task=%s", OCR_TASK_NAME)
    return True


async def shutdown_ocr_broker() -> None:
    """Đóng broker khi API shutdown."""
    try:
        broker = get_ocr_broker()
        await broker.shutdown()
    except Exception:
        logger.exception("ocr_queue.shutdown_failed")
    else:
        logger.info("ocr_queue.shutdown_ok")


async def enqueue_ocr_job(receipt_id: int) -> bool:
    """Push OCR job vào Redis queue.
    
    Returns:
        True: enqueue thành công
        False: fail (đã log lỗi với receipt_id để truy vết)
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
