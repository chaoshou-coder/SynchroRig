<# Tail SUMMARY.md in real time (Windows) #>
[CmdletBinding()]
param(
    [int]$Tail = 50
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$path = Join-Path $repoRoot "SUMMARY.md"

Write-Output ("[tail-summary] " + $path)
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -Path $path -Encoding UTF8 -Wait -Tail $Tail

