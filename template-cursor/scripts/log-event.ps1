<#
Append a subagent event to PROGRESS.md timeline and SUMMARY.md log (Chinese, timestamped).

Example:
  .\.cursor\scripts\log-event.ps1 -Subagent planner -Phase plan -What "拆分大任务" -Result "生成 5 个子任务" -Next "开始实现第 1 个"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("orchestrator","planner","implementers","verifier","skill","system")]
    [string]$Subagent,

    [Parameter(Mandatory = $true)]
    [string]$Phase,

    [Parameter(Mandatory = $true)]
    [string]$What,

    [string]$Result = "",
    [string]$Next = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
Push-Location $repoRoot
try {
    python -X utf8 -u .\.cursor\scripts\progress_tools.py event `
        --subagent $Subagent `
        --phase $Phase `
        --what $What `
        --result $Result `
        --next $Next
}
finally {
    Pop-Location
}

