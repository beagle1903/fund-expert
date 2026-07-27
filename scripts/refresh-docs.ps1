$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonScripts = Join-Path $RepoRoot ".venv\Scripts"
$Pdoc = Join-Path $PythonScripts "pdoc.exe"
$DocsRoot = Join-Path $RepoRoot "docs"
$PackageRoot = Join-Path $RepoRoot "fundexpert"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

& $Pdoc --no-show-source -o $DocsRoot $PackageRoot
if ($LASTEXITCODE -ne 0) {
    throw "pdoc failed with exit code $LASTEXITCODE."
}

Get-ChildItem -LiteralPath $DocsRoot -Recurse -File |
    Where-Object { $_.Extension -in ".html", ".js" } |
    ForEach-Object {
        $Path = $_.FullName
        $Text = [System.IO.File]::ReadAllText($Path)
        $Clean = [System.Text.RegularExpressions.Regex]::Replace(
            $Text,
            "[ \t]+(?=\r?$)",
            "",
            [System.Text.RegularExpressions.RegexOptions]::Multiline
        )
        if ($Clean -eq $Text) {
            return
        }

        for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
            try {
                [System.IO.File]::WriteAllText($Path, $Clean, $Utf8NoBom)
                break
            }
            catch {
                if ($Attempt -eq 3) {
                    throw
                }
                Start-Sleep -Milliseconds 100
            }
        }
    }
