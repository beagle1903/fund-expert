[CmdletBinding()]
param(
    [string]$EngineRoot,
    # API port. Falls back to FUNDEXPERT_API_PORT, then 8000. The Vite proxy
    # reads the same variable, so both sides always agree.
    [string]$ApiPort,
    # UI port. Falls back to FUNDEXPERT_UI_PORT, then 5173.
    [string]$UiPort
)

$ErrorActionPreference = "Stop"

function Resolve-Port {
    param(
        [string]$Value,
        [string]$EnvValue,
        [int]$Default
    )

    $source = "$Default"
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $source = $Value
    }
    elseif (-not [string]::IsNullOrWhiteSpace($EnvValue)) {
        $source = $EnvValue
    }
    $number = 0
    $valid = (
        [int]::TryParse($source.Trim(), [ref]$number) -and
        $number -ge 1 -and $number -le 65535
    )
    if (-not $valid) {
        $number = $Default
    }
    return @{ Source = $source; Valid = $valid; Number = $number }
}

$apiPortInfo = Resolve-Port -Value $ApiPort -EnvValue $env:FUNDEXPERT_API_PORT -Default 8000
$uiPortInfo = Resolve-Port -Value $UiPort -EnvValue $env:FUNDEXPERT_UI_PORT -Default 5173
$apiPortNumber = $apiPortInfo.Number
$uiPortNumber = $uiPortInfo.Number
$apiBase = "http://127.0.0.1:$apiPortNumber"
$apiUrl = "$apiBase/openapi.json"
$uiUrl = "http://127.0.0.1:$uiPortNumber/"

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

function Get-StatusCode {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return [int]$response.StatusCode
    }
    catch {
        $failed = $_.Exception.Response
        if ($null -ne $failed) {
            return [int]$failed.StatusCode
        }
        return $null
    }
}

function Get-LogTail {
    param([string]$Path)

    if (-not [string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path)) {
        return @((Get-Content -LiteralPath $Path -Tail 20 -ErrorAction SilentlyContinue))
    }
    return @()
}

function Get-ListenerProcessId {
    param([int]$Port)

    try {
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
            Where-Object {
                $_.LocalAddress -in @("127.0.0.1", "::1", "0.0.0.0", "::")
            }
        return $listeners | Select-Object -First 1 -ExpandProperty OwningProcess
    }
    catch {
        return $null
    }
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)

    try {
        return (
            Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        ).CommandLine
    }
    catch {
        return $null
    }
}

function Test-ProcessBelongsToRoot {
    param(
        [int]$ProcessId,
        [string]$Root
    )

    $rootNorm = $Root.TrimEnd("\", "/").ToLowerInvariant()
    $currentId = $ProcessId
    for ($i = 0; $i -lt 8 -and $null -ne $currentId -and $currentId -gt 0; $i++) {
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$currentId" -ErrorAction Stop
        }
        catch {
            return $false
        }
        foreach ($value in @($proc.ExecutablePath, $proc.CommandLine)) {
            if (-not [string]::IsNullOrWhiteSpace($value) -and
                $value.ToLowerInvariant().Contains($rootNorm)) {
                return $true
            }
        }
        $currentId = $proc.ParentProcessId
    }
    return $false
}

function Write-RunJson {
    param(
        [hashtable]$Payload
    )

    [Console]::Out.WriteLine(($Payload | ConvertTo-Json -Depth 6 -Compress))
    [Console]::Out.Flush()
}

function New-ErrorPayload {
    param(
        [string]$Message,
        [string]$EngineRootValue,
        $Api,
        $Ui,
        $Logs,
        [object[]]$ApiLogTail = @(),
        [object[]]$UiLogTail = @()
    )

    return [ordered]@{
        status = "error"
        error = $Message
        engine_root = $EngineRootValue
        url = $uiUrl
        api_url = $apiUrl
        api = $Api
        ui = $Ui
        logs = $Logs
        api_log_tail = $ApiLogTail
        ui_log_tail = $UiLogTail
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
    Write-RunJson (New-ErrorPayload -Message "Fund Expert repository not found. Set FUND_EXPERT_ROOT or pass -EngineRoot." -EngineRootValue $null -Api $null -Ui $null -Logs $null)
    exit 1
}
$portError = $null
if (-not $apiPortInfo.Valid) {
    $portError = "Invalid API port '$($apiPortInfo.Source)'. Pass -ApiPort or set FUNDEXPERT_API_PORT to a number from 1 to 65535."
}
elseif (-not $uiPortInfo.Valid) {
    $portError = "Invalid UI port '$($uiPortInfo.Source)'. Pass -UiPort or set FUNDEXPERT_UI_PORT to a number from 1 to 65535."
}
elseif ($apiPortNumber -eq $uiPortNumber) {
    $portError = "The API and UI cannot share port $apiPortNumber."
}
if ($null -ne $portError) {
    Write-RunJson (New-ErrorPayload -Message $portError -EngineRootValue $resolvedRoot -Api $null -Ui $null -Logs $null)
    exit 1
}

$logDir = Join-Path $resolvedRoot ".Agent\logs"
$apiStdout = Join-Path $logDir "fund-expert-api.stdout.log"
$apiStderr = Join-Path $logDir "fund-expert-api.stderr.log"
$uiStdout = Join-Path $logDir "fund-expert-vite.stdout.log"
$uiStderr = Join-Path $logDir "fund-expert-vite.stderr.log"
$logs = [ordered]@{
    api_stdout = $apiStdout
    api_stderr = $apiStderr
    ui_stdout = $uiStdout
    ui_stderr = $uiStderr
}
$apiState = [ordered]@{ status = "starting"; action = "started"; pid = $null }
$uiState = [ordered]@{ status = "starting"; action = "started"; pid = $null }

function Write-SetupFailure {
    param([string]$Message)

    Write-RunJson (
        New-ErrorPayload -Message $Message -EngineRootValue $resolvedRoot `
            -Api $apiState -Ui $uiState -Logs $logs `
            -ApiLogTail (Get-LogTail -Path $apiStderr) `
            -UiLogTail (Get-LogTail -Path $uiStderr)
    )
}

try {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null

    $apiPid = Get-ListenerProcessId -Port $apiPortNumber
    $uiPid = Get-ListenerProcessId -Port $uiPortNumber
    $apiReachable = Test-Endpoint -Url $apiUrl
    $uiReachable = Test-Endpoint -Url $uiUrl

    if ($null -ne $apiPid) {
        if (-not (Test-ProcessBelongsToRoot -ProcessId $apiPid -Root $resolvedRoot)) {
            $apiState.status = "conflict"
            $apiState.action = "rejected"
            $apiState.pid = $apiPid
            $cmd = Get-ProcessCommandLine -ProcessId $apiPid
            throw "Port $apiPortNumber is in use by process $apiPid, which does not belong to $resolvedRoot. Pass -ApiPort or set FUNDEXPERT_API_PORT to use another port. $cmd"
        }
        if (-not $apiReachable) {
            $apiState.status = "conflict"
            $apiState.action = "rejected"
            $apiState.pid = $apiPid
            throw "Port $apiPortNumber is already bound by this checkout but is not healthy at $apiUrl."
        }
        $apiState.status = "healthy"
        $apiState.action = "reused"
        $apiState.pid = $apiPid
    }
    elseif ($apiReachable) {
        $apiState.status = "conflict"
        $apiState.action = "rejected"
        throw "Port $apiPortNumber answered $apiUrl but the listener process could not be identified."
    }

    if ($null -ne $uiPid) {
        if (-not (Test-ProcessBelongsToRoot -ProcessId $uiPid -Root $resolvedRoot)) {
            $uiState.status = "conflict"
            $uiState.action = "rejected"
            $uiState.pid = $uiPid
            $cmd = Get-ProcessCommandLine -ProcessId $uiPid
            throw "Port $uiPortNumber is in use by process $uiPid, which does not belong to $resolvedRoot. Pass -UiPort or set FUNDEXPERT_UI_PORT to use another port. $cmd"
        }
        if (-not $uiReachable) {
            $uiState.status = "conflict"
            $uiState.action = "rejected"
            $uiState.pid = $uiPid
            throw "Port $uiPortNumber is already bound by this checkout but is not healthy at $uiUrl."
        }
        $uiState.status = "healthy"
        $uiState.action = "reused"
        $uiState.pid = $uiPid
    }
    elseif ($uiReachable) {
        $uiState.status = "conflict"
        $uiState.action = "rejected"
        throw "Port $uiPortNumber answered $uiUrl but the listener process could not be identified."
    }

    if ($apiState.action -ne "reused") {
        $python = Join-Path $resolvedRoot ".venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python)) {
            throw "Fund Expert Python runtime is missing: $python"
        }
        $apiProcess = Start-Process -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "fundexpert.api:app", "--host", "127.0.0.1", "--port", "$apiPortNumber") `
            -WorkingDirectory $resolvedRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $apiStdout -RedirectStandardError $apiStderr
        $apiState.pid = $apiProcess.Id
        Set-Content -LiteralPath (Join-Path $logDir "fund-expert-api.pid") -Value $apiProcess.Id
    }

    if ($uiState.action -ne "reused") {
        $frontendRoot = Join-Path $resolvedRoot "frontend"
        $vite = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
        $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($null -eq $npmCommand) {
            throw "npm.cmd is missing."
        }
        $npm = $npmCommand.Source
        if (-not (Test-Path -LiteralPath $vite)) {
            & $npm ci --prefix $frontendRoot
            if ($LASTEXITCODE -ne 0) {
                throw "npm ci failed with exit code $LASTEXITCODE."
            }
        }
        # vite.config.js reads this to pick the /api proxy target.
        $env:FUNDEXPERT_API_PORT = "$apiPortNumber"
        $uiProcess = Start-Process -FilePath $npm `
            -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$uiPortNumber", "--strictPort") `
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

    if ($apiHealthy) {
        $apiState.status = "healthy"
        if ($apiState.action -eq "started") {
            $apiState.pid = Get-ListenerProcessId -Port $apiPortNumber
        }
    }
    else {
        $apiState.status = "failed"
    }
    if ($uiHealthy) {
        $uiState.status = "healthy"
        if ($uiState.action -eq "started") {
            $uiState.pid = Get-ListenerProcessId -Port $uiPortNumber
        }
    }
    else {
        $uiState.status = "failed"
    }

    if (-not ($apiHealthy -and $uiHealthy)) {
        Write-SetupFailure "API or UI did not become healthy within 60 seconds."
        exit 1
    }

    # A reused Vite keeps the proxy target it was started with, so confirm
    # /api on the UI answers the same way as this API.
    $statusPath = "api/data-status"
    $directStatus = Get-StatusCode -Url "$apiBase/$statusPath"
    $proxiedStatus = Get-StatusCode -Url "$uiUrl$statusPath"
    if ($null -eq $directStatus -or $directStatus -ne $proxiedStatus) {
        $uiState.status = "conflict"
        throw "The UI on port $uiPortNumber does not proxy /api to the API on port $apiPortNumber (direct status $directStatus, proxied status $proxiedStatus). Stop the Vite process $($uiState.pid) and run again."
    }
}
catch {
    Write-SetupFailure $_.Exception.Message
    exit 1
}

Write-RunJson ([ordered]@{
    status = "success"
    engine_root = $resolvedRoot
    url = $uiUrl
    api_url = $apiUrl
    api = $apiState
    ui = $uiState
    logs = $logs
})
