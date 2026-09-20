[CmdletBinding()]
param(
    [string]$EngineRoot
)

$ErrorActionPreference = "Stop"
$apiUrl = "http://127.0.0.1:8000/openapi.json"
$uiUrl = "http://127.0.0.1:5173/"

function Test-FundExpertRoot {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    return (
        (Test-Path -LiteralPath (Join-Path $Path "fundexpert\__init__.py")) -and
        (Test-Path -LiteralPath (Join-Path $Path "frontend\package.json")) -and
        (Test-Path -LiteralPath (Join-Path $Path "fundexpert\api.py"))
    )
}

function Test-Endpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Get-LogTail {
    param([string]$Path)

    if (Test-Path -LiteralPath $Path) {
        return @((Get-Content -LiteralPath $Path -Tail 20 -ErrorAction SilentlyContinue))
    }
    return @()
}

function Get-ListenerProcessId {
    param([int]$Port)

    try {
        return Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port `
            -State Listen -ErrorAction Stop |
            Select-Object -First 1 -ExpandProperty OwningProcess
    }
    catch {
        return $null
    }
}

$scriptRepo = Split-Path -Parent $PSScriptRoot
$rootCandidates = @(
    $EngineRoot,
    $env:FUND_EXPERT_ROOT,
    $scriptRepo,
    (Get-Location).Path
)
$resolvedRoot = $null
foreach ($candidate in $rootCandidates) {
    if (Test-FundExpertRoot -Path $candidate) {
        $resolvedRoot = (Resolve-Path -LiteralPath $candidate).Path
        break
    }
}
if ($null -eq $resolvedRoot) {
    throw "Fund Expert repository not found. Set FUND_EXPERT_ROOT or pass -EngineRoot."
}

$logDir = Join-Path $resolvedRoot ".Agent\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$apiHealthy = Test-Endpoint -Url $apiUrl
$uiHealthy = Test-Endpoint -Url $uiUrl
$apiState = [ordered]@{ status = if ($apiHealthy) { "healthy" } else { "starting" }; action = if ($apiHealthy) { "reused" } else { "started" }; pid = $null }
$uiState = [ordered]@{ status = if ($uiHealthy) { "healthy" } else { "starting" }; action = if ($uiHealthy) { "reused" } else { "started" }; pid = $null }

$apiStdout = Join-Path $logDir "fund-expert-api.stdout.log"
$apiStderr = Join-Path $logDir "fund-expert-api.stderr.log"
$uiStdout = Join-Path $logDir "fund-expert-vite.stdout.log"
$uiStderr = Join-Path $logDir "fund-expert-vite.stderr.log"

if (-not $apiHealthy) {
    $python = Join-Path $resolvedRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Fund Expert Python runtime is missing: $python"
    }
    $apiProcess = Start-Process -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "fundexpert.api:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $resolvedRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $apiStdout -RedirectStandardError $apiStderr
    $apiState.pid = $apiProcess.Id
    Set-Content -LiteralPath (Join-Path $logDir "fund-expert-api.pid") -Value $apiProcess.Id
}

if (-not $uiHealthy) {
    $frontendRoot = Join-Path $resolvedRoot "frontend"
    $vite = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    if (-not (Test-Path -LiteralPath $vite)) {
        & $npm ci --prefix $frontendRoot
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed with exit code $LASTEXITCODE."
        }
    }
    $uiProcess = Start-Process -FilePath $npm `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort") `
        -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $uiStdout -RedirectStandardError $uiStderr
    $uiState.pid = $uiProcess.Id
    Set-Content -LiteralPath (Join-Path $logDir "fund-expert-vite.pid") -Value $uiProcess.Id
}

$deadline = [DateTime]::UtcNow.AddSeconds(60)
do {
    $apiHealthy = Test-Endpoint -Url $apiUrl
    $uiHealthy = Test-Endpoint -Url $uiUrl
    if ($apiHealthy -and $uiHealthy) {
        break
    }
    Start-Sleep -Seconds 1
} while ([DateTime]::UtcNow -lt $deadline)

$apiState.status = if ($apiHealthy) { "healthy" } else { "failed" }
$uiState.status = if ($uiHealthy) { "healthy" } else { "failed" }
if ($apiHealthy -and $apiState.action -eq "started") {
    $apiState.pid = Get-ListenerProcessId -Port 8000
}
if ($uiHealthy -and $uiState.action -eq "started") {
    $uiState.pid = Get-ListenerProcessId -Port 5173
}

if (-not ($apiHealthy -and $uiHealthy)) {
    $errorPayload = [ordered]@{
        status = "error"
        engine_root = $resolvedRoot
        url = $uiUrl
        api_url = $apiUrl
        api = $apiState
        ui = $uiState
        logs = [ordered]@{
            api_stdout = $apiStdout
            api_stderr = $apiStderr
            ui_stdout = $uiStdout
            ui_stderr = $uiStderr
        }
        api_log_tail = Get-LogTail -Path $apiStderr
        ui_log_tail = Get-LogTail -Path $uiStderr
    }
    [Console]::Out.WriteLine(($errorPayload | ConvertTo-Json -Depth 6 -Compress))
    [Console]::Out.Flush()
    exit 1
}

$successPayload = [ordered]@{
    status = "success"
    engine_root = $resolvedRoot
    url = $uiUrl
    api_url = $apiUrl
    api = $apiState
    ui = $uiState
    logs = [ordered]@{
        api_stdout = $apiStdout
        api_stderr = $apiStderr
        ui_stdout = $uiStdout
        ui_stderr = $uiStderr
    }
}
[Console]::Out.WriteLine(($successPayload | ConvertTo-Json -Depth 5 -Compress))
[Console]::Out.Flush()
