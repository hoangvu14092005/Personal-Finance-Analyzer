"""Manual/cron entry để purge các tài khoản đã quá grace period.

Chạy trực tiếp (không cần broker/Redis):
    python run_account_purge.py

Phù hợp gắn vào cron (Linux) hoặc Task Scheduler (Windows) chạy hằng ngày.
"""
from __future__ import annotations

from pfa_shared.storage import build_storage_service
from sqlmodel import Session

from account_purge import run_purge_due_accounts
from worker_app import engine, settings


def main() -> None:
    storage = build_storage_service(settings)
    with Session(engine) as session:
        result = run_purge_due_accounts(session, storage)
    print(
        f"Account purge done: purged={len(result.purged_user_ids)} "
        f"user_ids={result.purged_user_ids} "
        f"storage_files_deleted={result.storage_keys_deleted} "
        f"errors={result.storage_errors}",
    )


if __name__ == "__main__":
    main()
