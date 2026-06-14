param(
    [Parameter(Mandatory=$true)]
    [string]$TestName
)

$MaxAttempts = 5
$Attempt = 1

while ($Attempt -le $MaxAttempts) {
    Write-Host "Auto-heal attempt $Attempt / $MaxAttempts for $TestName"
    
    # Run the test
    $TestOutput = .venv\Scripts\python.exe -m pytest -k $TestName 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Test passed! Auto-healing complete." -ForegroundColor Green
        exit 0
    }
    
    Write-Host "Test failed. Invoking Agent to diagnose and fix..." -ForegroundColor Yellow
    
    # Pipe output to Agent for fixing
    $Prompt = @"
The test '$TestName' failed with the following output:
$TestOutput

You are an auto-healing agent. 
Diagnose the failure, apply the fix to the source code, and then exit.
Do not prompt for confirmation.
"@

    Agent -p $Prompt
    
    $Attempt++
}

Write-Host "Failed to auto-heal $TestName after $MaxAttempts attempts." -ForegroundColor Red
exit 1
