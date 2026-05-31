# Personal Finance Analyzer Worker

TaskIQ worker process for background jobs.

## Prerequisites

- Python 3.12+
- Redis available at `localhost:6379` (or set `REDIS_URL`)
- `uv` (or use `python -m uv`)

## Install dependencies

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker"
python -m uv sync
```

## Run worker

> **Lưu ý:** phải liệt kê các module chứa task (`tasks`, `index_tasks`) sau
> `worker_app:broker`, nếu không TaskIQ sẽ không đăng ký `process_ocr_job` /
> `index_receipt_text` và job sẽ kẹt ở trạng thái "processing".

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" taskiq worker --app-dir "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" worker_app:broker tasks index_tasks
```

## Dispatch demo task

Use a second terminal while worker is running:

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker\run_ping.py"
```

Expected output:

```text
ping
```

Worker terminal should log execution of `ping_task`.

## Account purge job (G1)

Khi user yêu cầu xóa tài khoản, hệ thống set `account_deletion_scheduled_at`
(grace period 14 ngày). Job purge xóa vĩnh viễn dữ liệu các tài khoản đã quá hạn
(và chưa hủy yêu cầu): toàn bộ transactions/receipts/budgets/insights/chat của
user + file receipt + file export trên storage. Merchants (dữ liệu global) và
system categories KHÔNG bị xóa.

Chạy thủ công / qua cron (không cần Redis):

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker\run_account_purge.py"
```

Gắn vào Windows Task Scheduler hoặc cron để chạy hằng ngày. Job là idempotent —
chạy lại an toàn (chỉ xử lý tài khoản tới hạn).

## Quality checks (Task 0.9)

Install dev dependencies:

```powershell
python -m uv sync --all-groups
```

Run lint, typecheck, tests:

```powershell
python -m uv run ruff check . tests
python -m uv run mypy .
python -m uv run pytest
```