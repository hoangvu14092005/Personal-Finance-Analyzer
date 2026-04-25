from __future__ import annotations

import logging

# Hàm get_logger(): Tạo một logger với tên và level tùy chỉnh
def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    return logging.getLogger(name)
