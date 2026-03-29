# Personal Finance Analyzer

Monorepo cho ung dung quan ly chi tieu ca nhan, gom frontend, backend API, worker va local infrastructure.

## Repository Structure (Phase 0.1)

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

Chua hoan thanh:
- Cac task tiep theo trong phase 0 (schema, quality baseline, CI)

### 1) Prerequisites

- Node.js 20+
- pnpm
- Python 3.12+
- uv (hoac su dung `python -m uv`)

### 2) Run Backend API

PowerShell:

```powershell
Set-Location "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\api"
python -m uv sync
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

### 2.1) Run Local Infra (Task 0.6)

Luu y: can mo Docker Desktop (hoac Docker daemon) truoc khi chay `docker compose up -d`.

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
- Backend API docs: http://127.0.0.1:8000/docs

### 4) Common Pitfall

- Neu chay uvicorn trong `backend/api/app` voi `main:app` se de loi import.
- Cach dung: chay tu `backend/api` voi `app.main:app` nhu lenh o tren.
- Khong dung `uv run uvicorn main:app --reload` trong `backend/api/app`.

### 5) Run Worker (Task 0.4)

Can Redis chay tai `localhost:6379`.

PowerShell:

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" taskiq worker --app-dir "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" worker_app:broker
```

Mo terminal khac de ban demo task:

```powershell
python -m uv run --project "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker" python "D:\VuLapTrinh2\Personal_Finance_Analyzer\backend\worker\run_ping.py"
```

Expected output:

```text
ping
```

### 6) Environment Files

Copy env examples thanh `.env` (neu can custom gia tri local):

- `frontend/web/.env.example`
- `backend/api/.env.example`
- `backend/worker/.env.example`

## Local Run (Roadmap)

Phase 0 dang duoc thuc hien tung buoc. Luong chay local day du se hoan thien o cac task tiep theo:

1. `0.2`: Khoi tao frontend
2. `0.3`: Khoi tao backend API
3. `0.4`: Khoi tao worker
4. `0.5`: Cau hinh shared Python package cho API/worker
5. `0.6`: Cau hinh local infra (PostgreSQL, Redis, MinIO)

Sau khi hoan thanh cac task tren, du an se ho tro chay local end-to-end.

## Current Status

- [x] Phase 0.1: Tao boundary thu muc frontend/backend/worker
- [x] Phase 0.2: Frontend skeleton (Next.js 15 + Tailwind + TypeScript)
- [x] Phase 0.3: Backend API skeleton (FastAPI + uv + GET /health)
- [x] Phase 0.4: Worker skeleton (TaskIQ + Redis + ping_task)
- [x] Phase 0.5: Shared package skeleton (config/logging/enums/schemas/utils)
- [x] Phase 0.6: Local infra skeleton (PostgreSQL + Redis + MinIO + init bucket + env examples)
- [ ] Cac task con lai trong phase 0
