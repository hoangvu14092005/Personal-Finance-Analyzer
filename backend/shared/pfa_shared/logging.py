"""Logging configuration dùng chung.

Format: "timestamp level [name] message"
Example: "2026-05-01 10:30:45 INFO [worker] Processing receipt 123"
"""
from __future__ import annotations

import logging


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Tạo logger với format chuẩn.
    
    Args:
        name: Logger name (e.g., "worker", "api")
        level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    return logging.getLogger(name)
