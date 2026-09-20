$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-RepoPython {
    $windows = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    $unix = Join-Path $RepoRoot ".venv\bin\python"
    if (Test-Path -LiteralPath $windows) {
        return $windows
    }
    if (Test-Path -LiteralPath $unix) {
        return $unix
    }
    throw "Python venv is missing. Create .venv and install -e `".[dev,web]`"."
}

function Get-Npm {
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -ne $npmCmd) {
        return $npmCmd.Source
    }
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($null -ne $npm) {
        return $npm.Source
    }
    throw "npm is missing."
}

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

$Python = Get-RepoPython
$Npm = Get-Npm

Push-Location $RepoRoot
try {
    & $Python -m pytest tests/
    Assert-LastExitCode "Python tests"

    & $Npm --prefix frontend test
    Assert-LastExitCode "Frontend tests"

    & $Npm --prefix frontend run lint
    Assert-LastExitCode "Frontend lint"

    & $Npm --prefix frontend run build
    Assert-LastExitCode "Frontend build"

    & $Python -m vulture fundexpert --min-confidence 80
    Assert-LastExitCode "Dead-code analysis"

    & $Python -m pip check
    Assert-LastExitCode "Dependency check"

    & git diff --check
    Assert-LastExitCode "Whitespace check"
}
finally {
    Pop-Location
}
