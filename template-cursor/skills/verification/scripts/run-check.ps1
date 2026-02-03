<# 
Runs the project verification suite.

- Preferred: `make check` (if `make` is available)
- Fallback (Windows-friendly): run the underlying Python commands directly

Exit codes:
- 0 on success (prints "All checks passed!")
- non-zero on failure
#>

[CmdletBinding()]
param(
    [switch]$Json,
    [switch]$NoMake
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Output ("==> " + $Name)
    & $Action
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..\\..")

Push-Location $repoRoot
try {
    $makeCmd = $null
    if (-not $NoMake) {
        $makeCmd = Get-Command make -ErrorAction SilentlyContinue
    }

    if ($makeCmd) {
        & make check
        $exitCode = $LASTEXITCODE

        if ($Json) {
            if ($exitCode -eq 0) {
                Write-Output '{"status":"PASS","runner":"make","message":"All checks passed!"}'
            }
            else {
                Write-Output ('{"status":"FAIL","runner":"make","exit_code":' + $exitCode + "}")
            }
        }

        exit $exitCode
    }

    Invoke-Step -Name "Formatting" -Action { python -m ruff format . }
    Invoke-Step -Name "Auto-fix lint" -Action { python -m ruff check . --fix }
    Invoke-Step -Name "Linting" -Action { python -m ruff check . }
    Invoke-Step -Name "Running tests" -Action { python -m pytest -vv --tb=short tests/ }

    Write-Output "All checks passed!"
    if ($Json) {
        Write-Output '{"status":"PASS","runner":"python","message":"All checks passed!"}'
    }
    exit 0
}
catch {
    Write-Error $_
    if ($Json) {
        Write-Output '{"status":"FAIL","runner":"powershell","message":"Exception during verification."}'
    }
    exit 1
}
finally {
    Pop-Location
}

