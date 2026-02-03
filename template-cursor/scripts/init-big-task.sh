#!/usr/bin/env bash
set -euo pipefail

TITLE="${1:-}"
REQ="${2:-}"

if [[ -z "$TITLE" || -z "$REQ" ]]; then
  echo "Usage: init-big-task.sh \"<title>\" \"<requirement>\"" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STARTED_AT="$(date '+%Y-%m-%d %H:%M:%S')"

cat > "$REPO_ROOT/SUMMARY.md" <<EOF
# SUMMARY

> 大任务运行摘要（本次运行 append-only）

## 大任务

- **标题**：${TITLE}
- **开始时间**：${STARTED_AT}

### 需求原文/摘要

${REQ}

## 运行日志（按时间追加）

| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |
|---|---|---|---|---|---|

EOF

cat > "$REPO_ROOT/PROGRESS.md" <<EOF
# PROGRESS（进度条）

## 大任务

- **标题**：${TITLE}
- **开始时间**：${STARTED_AT}
- **当前时间**：${STARTED_AT}
- **总进度**：0/0（0%） [--------------------]

### 需求原文/摘要

${REQ}

## 子任务清单（PR 粒度）

| 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |
|---|---|---|---|---|---|---|

## 时间线（实时日志）

| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |
|---|---|---|---|---|---|

EOF

echo "Initialized SUMMARY.md and PROGRESS.md."

