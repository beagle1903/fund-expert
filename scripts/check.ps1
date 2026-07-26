$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

Push-Location $RepoRoot
try {
    & $Python -m pytest tests/
    Assert-LastExitCode "Python tests"

    & npm.cmd --prefix frontend test
    Assert-LastExitCode "Frontend tests"

    & npm.cmd --prefix frontend run lint
    Assert-LastExitCode "Frontend lint"

    & npm.cmd --prefix frontend run build
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
