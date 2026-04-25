"""
Module quản lý cấu hình logging cho API service.

Chức năng chính:
- Tự động thêm request_id vào mọi log message
- Cấu hình format và level cho logging
- Cung cấp factory function để tạo logger
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.middleware.request_context import get_request_id

# Biến toàn cục để đảm bảo log factory chỉ được setup 1 lần duy nhất (log factory = bộ tạo logger)
# Tránh việc gọi setLogRecordFactory() nhiều lần gây conflict
_LOG_RECORD_FACTORY_SET = False


def _set_log_record_factory() -> None:
    """
    Tùy chỉnh LogRecord factory để tự động thêm request_id vào mọi log.
    
    Cách hoạt động:
    1. Lưu lại factory cũ của Python logging
    2. Tạo factory mới wrap factory cũ
    3. Tự động inject request_id từ context vào mọi LogRecord
    4. Set factory mới làm default
    
    Chỉ chạy 1 lần duy nhất trong lifecycle của app.
    """
    global _LOG_RECORD_FACTORY_SET  # Cần global để sửa biến module-level
    
    # Guard clause: Nếu đã setup rồi thì return ngay
    if _LOG_RECORD_FACTORY_SET:
        return

    # Lưu lại factory gốc của Python logging
    old_factory = logging.getLogRecordFactory()

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        """
        Custom factory tạo LogRecord với request_id.
        
        Args:
            *args: Arguments truyền cho factory gốc
            **kwargs: Keyword arguments truyền cho factory gốc
            
        Returns:
            LogRecord đã được thêm attribute request_id
        """
        # Gọi factory gốc để tạo LogRecord như bình thường
        record = old_factory(*args, **kwargs)
        
        # Thêm request_id vào record nếu chưa có
        # request_id lấy từ ContextVar được set bởi RequestIdMiddleware
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        
        return record

    # Đăng ký factory mới làm default cho toàn bộ app
    logging.setLogRecordFactory(factory)
    
    # Đánh dấu đã setup để không setup lại lần nữa
    _LOG_RECORD_FACTORY_SET = True


def configure_logging() -> None:
    """
    Cấu hình logging cho toàn bộ application.
    
    Được gọi 1 lần khi app khởi động (trong main.py).
    
    Cấu hình:
    - Log level: Lấy từ settings (INFO, DEBUG, WARNING, ERROR...)
    - Format: Timestamp + Level + Logger name + Request ID + Message
    - Factory: Tự động thêm request_id vào mọi log
    
    Example log output:
        2024-01-15 10:30:45,123 INFO [api.request] [request_id=abc-123]
        request.start method=GET path=/api/v1/receipts
    """
    settings = get_settings()
    
    # Setup custom factory để inject request_id
    _set_log_record_factory()
    
    # Cấu hình logging cơ bản
    logging.basicConfig(
        # Log level: Chuyển string "INFO" -> logging.INFO constant
        # Nếu settings.log_level không hợp lệ, fallback về INFO
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        
        # Format string cho log messages
        # %(asctime)s: Timestamp (2024-01-15 10:30:45,123)
        # %(levelname)s: Log level (INFO, ERROR, DEBUG...)
        # %(name)s: Logger name (api.request, api.auth...)
        # %(request_id)s: Request ID từ custom factory
        # %(message)s: Log message thực tế
        format="%(asctime)s %(levelname)s [%(name)s] [request_id=%(request_id)s] %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """
    Factory function để tạo logger với tên cụ thể.
    
    Args:
        name: Tên của logger, thường là module path
              Ví dụ: "api.request", "api.auth", "api.receipts"
    
    Returns:
        Logger instance đã được cấu hình với request_id support
        
    Usage:
        logger = get_logger("api.receipts")
        logger.info("Processing receipt upload")
        # Output: 2024-01-15 10:30:45 INFO [api.receipts] [request_id=abc-123]
        # Processing receipt upload
    """
    return logging.getLogger(name)
