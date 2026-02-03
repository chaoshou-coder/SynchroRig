<#
Upsert a task row in PROGRESS.md and recompute progress/time.

Example:
  .\.cursor\scripts\upsert-task.ps1 -TaskId T1 -Desc "实现 X" -Risk medium -Status IN_PROGRESS -Evidence ""
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [Parameter(Mandatory = $true)][string]$Desc,
    [Parameter(Mandatory = $true)][ValidateSet("low","medium","high")][string]$Risk,
    [Parameter(Mandatory = $true)][ValidateSet("IN_PROGRESS","PASS","FAIL","BLOCKED")][string]$Status,
    [string]$Evidence = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
Push-Location $repoRoot
try {
    python -X utf8 -u .\.cursor\scripts\progress_tools.py task `
        --task-id $TaskId `
        --desc $Desc `
        --risk $Risk `
        --status $Status `
        --evidence $Evidence
}
finally {
    Pop-Location
}

