# Start toàn bộ stack: Docker infra + Backend API + Worker + Frontend
# Chạy từ root repo: .\start-all.ps1

$ErrorActionPreference = "Stop"
$ROOT = "D:\VuLapTrinh2\Personal_Finance_Analyzer"

Write-Host "==> 1/4 Starting Docker infrastructure..." -ForegroundColor Cyan
Set-Location "$ROOT\infra\docker"
docker compose up -d

Write-Host "==> Waiting for PostgreSQL + Redis to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 6

Write-Host "==> 2/4 Starting Backend API (port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ROOT\backend\api'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Write-Host "==> 3/4 Starting Worker (OCR + RAG indexing)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ROOT\backend\worker'; ..\api\.venv\Scripts\python.exe -m taskiq worker --app-dir . worker_app:broker tasks index_tasks"
)

Write-Host "==> 4/4 Starting Frontend (port 3000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ROOT\frontend\web'; corepack pnpm dev"
)

Set-Location $ROOT

Write-Host ""
Write-Host "All services starting..." -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "  Frontend     : http://localhost:3000"
Write-Host "  API docs     : http://127.0.0.1:8000/docs"
Write-Host "  MinIO Console: http://localhost:9001 (minioadmin / minioadmin)"
Write-Host ""
Write-Host "Dừng tất cả: .\stop-all.ps1"
