param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$EnvFile = Join-Path $Root ".env"
$ComposeFile = Join-Path $Root "infra\docker\docker-compose.yml"
$TmpDir = Join-Path $Root ".dev-stack"
$PidDir = Join-Path $TmpDir "pids"
$ApiDir = Join-Path $Root "backend\api"
$WorkerDir = Join-Path $Root "backend\worker"
$FrontendDir = Join-Path $Root "frontend\web"
$ApiPython = Join-Path $ApiDir ".venv\Scripts\python.exe"
$WorkerPython = Join-Path $WorkerDir ".venv\Scripts\python.exe"
$ApiPidFile = Join-Path $PidDir "api.pid"
$WorkerPidFile = Join-Path $PidDir "worker.pid"
$FrontendPidFile = Join-Path $PidDir "frontend.pid"

function Write-Step($Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok($Message) {
    Write-Host "    $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "    $Message" -ForegroundColor Yellow
}

function Get-EnvValue($Name, $Default) {
    if (-not (Test-Path $EnvFile)) {
        return $Default
    }

    $line = Get-Content $EnvFile |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } |
        Select-Object -First 1

    if (-not $line) {
        return $Default
    }

    $value = ($line -replace "^\s*$([regex]::Escape($Name))\s*=\s*", "").Trim()
    if (-not $value) {
        return $Default
    }

    return $value.Trim('"').Trim("'")
}

$ApiPort = [int](Get-EnvValue "PORT" "8001")
$FrontendPort = 3000
$ApiHealthUrl = "http://127.0.0.1:$ApiPort/health"
$FrontendUrl = "http://localhost:$FrontendPort"

function Ensure-Directories {
    New-Item -ItemType Directory -Force -Path $TmpDir, $PidDir | Out-Null
}

function Test-ProcessId($ProcessId) {
    if (-not $ProcessId) {
        return $false
    }

    return [bool](Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Read-Pid($Path) {
    if (-not (Test-Path $Path)) {
        return $null
    }

    $raw = (Get-Content $Path -ErrorAction SilentlyContinue | Select-Object -First 1)
    $pidValue = 0
    if ([int]::TryParse($raw, [ref]$pidValue)) {
        return $pidValue
    }

    return $null
}

function Stop-PidFile($Path, $Name) {
    $processId = Read-Pid $Path
    if ($processId -and (Test-ProcessId $processId)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Ok "Stopped $Name PID $processId"
    }

    if (Test-Path $Path) {
        Remove-Item -LiteralPath $Path -Force
    }
}

function Stop-Port($Port, $Name) {
    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($connection in $connections) {
        if ($connection.OwningProcess -and $connection.OwningProcess -ne 0) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Ok "Stopped $Name listener PID $($connection.OwningProcess) on port $Port"
        }
    }
}

function Stop-WorkerChildren {
    try {
        $needle = [regex]::Escape($WorkerDir)
        $processes = Get-CimInstance Win32_Process |
            Where-Object {
                $_.CommandLine -match "taskiq" -and $_.CommandLine -match $needle
            }
        foreach ($process in $processes) {
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Ok "Stopped worker child PID $($process.ProcessId)"
        }
    } catch {
        Write-Warn "Skipped worker child scan: $($_.Exception.Message)"
    }
}

function Wait-Http($Url, $Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 3
            return $response.StatusCode
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    return "ERR"
}

function Invoke-Docker($Arguments) {
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & docker @Arguments 2>&1
        return @{
            ExitCode = $LASTEXITCODE
            Output = $output
        }
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
}

function Start-LoggedProcess($Name, $FilePath, [string[]]$Arguments, $WorkingDirectory, $PidFile) {
    $existingPid = Read-Pid $PidFile
    if ($existingPid -and (Test-ProcessId $existingPid)) {
        Write-Warn "$Name already running with PID $existingPid"
        return
    }

    $outLog = Join-Path $TmpDir "pfa-$Name.out.log"
    $errLog = Join-Path $TmpDir "pfa-$Name.err.log"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $PidFile -Value $process.Id
    Write-Ok "Started $Name PID $($process.Id)"
}

function Start-Infra {
    Write-Step "Starting Docker infrastructure"
    $result = Invoke-Docker -Arguments @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "up", "-d")
    $result.Output
    if ($result.ExitCode -ne 0) {
        throw "Docker compose failed to start infrastructure."
    }
}

function Stop-Infra {
    Write-Step "Stopping Docker infrastructure"
    $result = Invoke-Docker -Arguments @("compose", "--env-file", $EnvFile, "-f", $ComposeFile, "stop")
    $result.Output
    if ($result.ExitCode -ne 0) {
        Write-Warn "Docker compose stop failed. Docker may be closed or require elevated permission."
    }
}

function Start-App {
    Ensure-Directories
    Start-Infra

    Write-Step "Applying database migrations"
    & $ApiPython -m alembic upgrade head

    Write-Step "Seeding default categories"
    & $ApiPython -m scripts.seed_categories

    Write-Step "Starting Backend API on port $ApiPort"
    Start-LoggedProcess `
        -Name "api" `
        -FilePath $ApiPython `
        -Arguments @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$ApiPort") `
        -WorkingDirectory $ApiDir `
        -PidFile $ApiPidFile

    Write-Step "Starting Worker"
    Start-LoggedProcess `
        -Name "worker" `
        -FilePath $WorkerPython `
        -Arguments @("-m", "taskiq", "worker", "--app-dir", $WorkerDir, "worker_app:broker", "tasks", "index_tasks") `
        -WorkingDirectory $WorkerDir `
        -PidFile $WorkerPidFile

    Write-Step "Starting Frontend on port $FrontendPort"
    Start-LoggedProcess `
        -Name "frontend" `
        -FilePath "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "corepack pnpm dev") `
        -WorkingDirectory $FrontendDir `
        -PidFile $FrontendPidFile

    Write-Step "Checking services"
    $apiCode = Wait-Http $ApiHealthUrl 25
    $webCode = Wait-Http $FrontendUrl 35

    Write-Host ""
    Write-Host "PFA dev stack" -ForegroundColor Cyan
    Write-Host "  API health : $ApiHealthUrl -> $apiCode"
    Write-Host "  Frontend   : $FrontendUrl -> $webCode"
    Write-Host "  MinIO      : http://localhost:9001"
    Write-Host "  Logs       : $TmpDir\pfa-*.log"
    Write-Host ""
}

function Stop-App {
    Ensure-Directories
    Write-Step "Stopping app processes"
    Stop-PidFile $FrontendPidFile "frontend"
    Stop-PidFile $WorkerPidFile "worker"
    Stop-WorkerChildren
    Stop-PidFile $ApiPidFile "api"
    Stop-Port $FrontendPort "frontend"
    Stop-Port $ApiPort "api"
    Stop-Infra
}

function Show-Status {
    Ensure-Directories
    $apiPid = Read-Pid $ApiPidFile
    $workerPid = Read-Pid $WorkerPidFile
    $frontendPid = Read-Pid $FrontendPidFile
    $apiCode = Wait-Http $ApiHealthUrl 2
    $webCode = Wait-Http $FrontendUrl 2

    Write-Host "PFA dev stack status" -ForegroundColor Cyan
    Write-Host "  API PID      : $apiPid running=$(Test-ProcessId $apiPid) health=$apiCode"
    Write-Host "  Worker PID   : $workerPid running=$(Test-ProcessId $workerPid)"
    Write-Host "  Frontend PID : $frontendPid running=$(Test-ProcessId $frontendPid) web=$webCode"
    Write-Host ""
    $result = Invoke-Docker -Arguments @("ps", "--filter", "name=pfa-", "--format", "table {{.Names}}`t{{.Status}}`t{{.Ports}}")
    if ($result.ExitCode -eq 0) {
        $result.Output
    } else {
        Write-Warn "Docker status unavailable. Docker Desktop may be closed or require permission."
    }
}

switch ($Action) {
    "start" { Start-App }
    "stop" { Stop-App }
    "restart" {
        Stop-App
        Start-App
    }
    "status" { Show-Status }
}
