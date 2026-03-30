from __future__ import annotations

import logging

from app.core.config import get_settings
from app.middleware.request_context import get_request_id


_LOG_RECORD_FACTORY_SET = False


def _set_log_record_factory() -> None:
    global _LOG_RECORD_FACTORY_SET
    if _LOG_RECORD_FACTORY_SET:
        return

    old_factory = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        return record

    logging.setLogRecordFactory(factory)
    _LOG_RECORD_FACTORY_SET = True


def configure_logging() -> None:
    settings = get_settings()
    _set_log_record_factory()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
