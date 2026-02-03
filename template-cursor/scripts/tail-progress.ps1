<# Tail PROGRESS.md in real time (Windows) #>
[CmdletBinding()]
param(
    [int]$Tail = 50
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$path = Join-Path $repoRoot "PROGRESS.md"

Write-Output ("[tail-progress] " + $path)
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -Path $path -Encoding UTF8 -Wait -Tail $Tail

