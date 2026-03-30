from __future__ import annotations

import asyncio
import sys
from pathlib import Path


def enqueue_ocr_job(receipt_id: int) -> bool:
    worker_dir = Path(__file__).resolve().parents[3] / "worker"
    if str(worker_dir) not in sys.path:
        sys.path.append(str(worker_dir))

    try:
        from tasks import process_ocr_job  # type: ignore[import-not-found]

        asyncio.run(process_ocr_job.kiq(receipt_id))
        return True
    except Exception:
        return False
