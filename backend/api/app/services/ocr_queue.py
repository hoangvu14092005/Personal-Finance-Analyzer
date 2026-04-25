""" file này là cầu nối giữa phần backend chính và worker xử lý OCR, cho phép gửi job 
OCR một cách bất đồng bộ mà không cần biết chi tiết về worker. """

import asyncio
import os
import sys


def enqueue_ocr_job(receipt_id: int) -> bool:
    """
    Đẩy một job OCR vào hàng đợi xử lý bất đồng bộ.

    Args:
        receipt_id (int): ID của receipt cần xử lý OCR.

    Returns:
        bool: True nếu job được đẩy thành công, False nếu có lỗi.
    """
    try:
        # Tìm đường dẫn thư mục worker (3 cấp trên so với file hiện tại)
        worker_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../..", "worker")
        )

        # Thêm worker_dir vào sys.path để có thể import module từ đó
        if worker_dir not in sys.path:
            sys.path.insert(0, worker_dir)

        # Import task xử lý OCR từ module tasks trong worker.
        # TODO(M3): refactor thành shared task contract package thay vì sys.path injection.
        from tasks import process_ocr_job  # type: ignore[import-not-found]

        # Đẩy job vào queue bằng cú pháp Taskiq (.kiq = "kick")
        asyncio.run(process_ocr_job.kiq(receipt_id))

        return True
    except Exception:
        return False
