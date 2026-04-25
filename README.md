# Personal Finance Analyzer

Monorepo cho ung dung quan ly chi tieu ca nhan, gom frontend, backend API, worker va local infrastructure.

## Repository Structure

- `frontend/web`: Web app (Next.js)
- `backend/api`: FastAPI service
- `backend/worker`: Background worker
- `backend/shared`: Shared Python package dung chung cho API/worker
- `infra/docker`: Dockerfiles va local container setup
- `docs`: Tai lieu du an

## Local Run (Current)

Trang thai hien tai da chay duoc:
- Frontend (Next.js)
- Backend API (FastAPI)
- Worker (TaskIQ + Redis)
- Local infra (PostgreSQL, Redis, MinIO)
- Auth flow (register/login/logout/me)
- Receipt upload flow + polling status + OCR mock baseline

### One-shot (Copy 1 Block)

Chay block sau trong PowerShell tai root repo `D:\VuLapTrinh2\Personal_Finance_Analyzer`.
Block nay se:
- up local infra (PostgreSQL, Redis, MinIO),
- mo 3 terminal rieng cho API, worker, frontend,
- in ra URL de check nhanh.

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer"

# 1) Start infra
Set-Location "infra\docker"
docker compose up -d
Set-Location "..\.."

# 2) Start API in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api'; python -m uv sync --all-groups; python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)

# 3) Start worker in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker'; python -m uv sync --all-groups; python -m uv run taskiq worker --app-dir 'D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker' worker_app:broker"
)

# 4) Start frontend in new terminal
Start-Process powershell -ArgumentList @(
	"-NoExit",
	"-Command",
	"Set-Location 'D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web'; pnpm install; pnpm dev"
)

Write-Host "Infra/API/Worker/Frontend are starting..."
Write-Host "API health: http://127.0.0.1:8000/health"
Write-Host "Frontend : http://localhost:3000"
Write-Host "API docs : http://127.0.0.1:8000/docs"
```

### 1) Prerequisites

- Node.js 20+
- pnpm
- Python 3.12+
- uv (hoac su dung `python -m uv`)
- Docker Desktop (hoac Docker daemon)

### 2) Run Backend API

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api"
python -m uv sync --all-groups
python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Neu ban muon chay tu bat ky thu muc nao (an toan hon), dung lenh nay:

```powershell
python -m uv run uvicorn --app-dir "D:/VuLapTrinh2/Personal_Finance_Analyzer/backend/api" app.main:app --reload --host 0.0.0.0 --port 8000
```

Kiem tra health:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

Expected:

```json
{"status":"ok","service":"api"}
```

### 2.1) Run Local Infra

Luu y: can mo Docker Desktop (hoac Docker daemon) truoc khi chay command.

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\infra\docker"
docker compose up -d
docker compose ps
```

Services:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

MinIO default credentials:
- username: `minioadmin`
- password: `minioadmin`

Bucket `pfa-receipts` duoc tao tu dong boi init service `minio-init`.

Kiem tra nhanh init logs:

```powershell
docker compose logs minio-init
```

Dung local infra:

```powershell
docker compose down
```

### 3) Run Frontend

Mo terminal khac, chay:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web"
pnpm install
pnpm dev
```

Mo trinh duyet:
- Frontend home: http://localhost:3000
- Frontend health page: http://localhost:3000/health
- Frontend login page: http://localhost:3000/login
- Frontend register page: http://localhost:3000/register
- Frontend dashboard (protected): http://localhost:3000/dashboard
- Frontend receipt upload: http://localhost:3000/receipts/upload
- Backend API docs: http://127.0.0.1:8000/docs

### 4) Run Worker

Can Redis chay tai `localhost:6379`.

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker"
python -m uv sync --all-groups
python -m uv run taskiq worker --app-dir "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" worker_app:broker
```

Mo terminal khac de ban demo task:

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker\run_ping.py"
```

Expected output:

```text
ping
```

### 5) Test Commands

#### Frontend

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\frontend\web"
pnpm lint
pnpm build
```

#### Backend API

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api"
python -m uv sync --all-groups
python -m uv run ruff check app tests
python -m uv run mypy app
python -m uv run pytest
```

#### Backend Worker

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker"
python -m uv sync --all-groups
python -m uv run ruff check . tests
python -m uv run mypy .
python -m uv run pytest
```

### 6) Quick Manual Test (Auth + Receipt Upload)

1. Start infra, API, frontend (va worker neu muon OCR queue consume).
2. Mo `http://localhost:3000/register`, tao tai khoan moi.
3. Dang nhap o `http://localhost:3000/login`.
4. Vao `http://localhost:3000/receipts/upload`, upload file JPG/PNG/PDF.
5. Xac nhan UI hien trang thai `uploading -> processing -> ready/failed`.
6. Neu failed/timeout, kiem tra fallback manual-entry message tren UI.

### 7) Environment Files

Copy env examples thanh `.env` (neu can custom gia tri local):

- `frontend/web/.env.example`
- `backend/api/.env.example`
- `backend/worker/.env.example`

### 8) Common Pitfall

- Neu chay uvicorn trong `backend/api/app` voi `main:app` se de loi import.
- Cach dung: chay tu `backend/api` voi `app.main:app` nhu lenh o tren.
- Khong dung `uv run uvicorn main:app --reload` trong `backend/api/app`.

### 9) Transaction APIs (Phase 3 baseline)

Sau khi dang nhap (cookie `pfa_session` da duoc set), co the goi:

- `POST /api/v1/transactions` - tao transaction (manual entry hoac tu OCR draft).
  Body toi thieu:

  ```json
  {
    "amount": "125000.00",
    "currency": "VND",
    "transaction_date": "2026-04-01",
    "merchant_name": "Pho 24",
    "category_id": 3,
    "note": "Lunch with team"
  }
  ```

  Optional `receipt_upload_id` de link voi receipt da OCR; phai thuoc cung user.

- `GET /api/v1/transactions` - list transaction co filter:

  | Query param | Mo ta |
  | --- | --- |
  | `start_date` | ISO date, transaction tu ngay nay tro di |
  | `end_date` | ISO date, transaction den het ngay nay |
  | `category_id` | Loc theo category, > 0 |
  | `merchant` | Substring match (case-insensitive) cho `merchant_name` |
  | `page` | Default `1`, >= 1 |
  | `size` | Default `20`, max `100` |

  Response shape:

  ```json
  {
    "items": [{ "id": 1, "amount": "125000.00", "...": "..." }],
    "meta": { "total": 42, "page": 1, "size": 20 }
  }
  ```

## Current Status

- [x] Phase 0: Foundation
- [x] Phase 1: Auth and session
- [x] Phase 2: Receipt upload and OCR pipeline baseline
- [ ] Phase 3: Transactions and review (M1 done: schemas + create + list)
