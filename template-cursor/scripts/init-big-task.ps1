<#
Initialize SUMMARY.md and PROGRESS.md for a new big task.

This is designed for Windows. It overwrites both files.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$Requirement
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..")
$startedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$summaryPath = Join-Path $repoRoot "SUMMARY.md"
$progressPath = Join-Path $repoRoot "PROGRESS.md"

$summary = @"
# SUMMARY

> 大任务运行摘要（本次运行 append-only）

## 大任务

- **标题**：$Title
- **开始时间**：$startedAt

### 需求原文/摘要

$Requirement

## 运行日志（按时间追加）

| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |
|---|---|---|---|---|---|

"@

$progress = @"
# PROGRESS（进度条）

## 大任务

- **标题**：$Title
- **开始时间**：$startedAt
- **当前时间**：$startedAt
- **总进度**：0/0（0%） [--------------------]

### 需求原文/摘要

$Requirement

## 子任务清单（PR 粒度）

| 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |
|---|---|---|---|---|---|---|

## 时间线（实时日志）

| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |
|---|---|---|---|---|---|

"@

Set-Content -Path $summaryPath -Value $summary -Encoding UTF8
Set-Content -Path $progressPath -Value $progress -Encoding UTF8

Write-Output "Initialized SUMMARY.md and PROGRESS.md."

