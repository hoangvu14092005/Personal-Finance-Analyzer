# Dừng toàn bộ stack.

$ROOT = "D:\VuLapTrinh2\Personal_Finance_Analyzer"

Write-Host "==> Stopping Docker services..." -ForegroundColor Cyan
Set-Location "$ROOT\infra\docker"
docker compose down

Write-Host "==> Killing Python + Node processes (uvicorn/taskiq/next)..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "uvicorn|taskiq" } |
    Stop-Process -Force -ErrorAction SilentlyContinue

Get-Process node -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "next" } |
    Stop-Process -Force -ErrorAction SilentlyContinue

Set-Location $ROOT

Write-Host ""
Write-Host "Stopped." -ForegroundColor Green
Write-Host "Note: nếu terminal API/Worker/Frontend vẫn mở, đóng tay bằng Ctrl+C."
