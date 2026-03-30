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

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" taskiq worker --app-dir "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" worker_app:broker
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