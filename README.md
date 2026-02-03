# SynchroRig

一个可直接复制到任意仓库的 Cursor 工作流模板：用户只输入“大任务”，系统自动按规则轮流调用 subagents（planner → implementers → verifier）完成拆分、实现、验收，并把全过程动态写入 `SUMMARY.md` 与 `PROGRESS.md`。

## 快速开始

### 1) 安装开发依赖（本仓库示例）

```powershell
python -m pip install -r .\requirements-dev.txt
```

### 2) 验证环境（本仓库示例）

```powershell
.\.cursor\skills\verification\scripts\run-check.ps1
```

看到 `All checks passed!` 即表示本仓库的最小验收链路可跑通。

## 在你的项目里使用这个模板

把 `template-cursor/` 复制到你的项目根目录并改名为 `.cursor/`：

```powershell
Copy-Item -Recurse -Force .\template-cursor .\.cursor
```

然后在 Cursor 中打开你的项目目录，确保 Rules / Skills / Subagents 都能被加载。

## 大任务工作流（你期望的“只输入我要做的事”）

### 入口

你只需要在 Agent Chat 里输入你的大任务需求（不要手动调用任何 `/planner`、`/implementers`、`/verifier`）。

### 初始化（每次大任务开始都会重置文件）

工作流要求在每个大任务开始时覆盖重写：

- `SUMMARY.md`
- `PROGRESS.md`

Windows 可用脚本（也可由 Orchestrator 按规则自动执行）：

```powershell
.\.cursor\scripts\init-big-task.ps1 -Title "大任务标题" -Requirement "大任务原话/高保真摘要"
```

### 轮转执行

- `/planner`：把大任务拆成 PR-sized 子任务（带 risk_level 与 parallel_count）
- `/implementers`：对每个子任务按 parallel_count 并行产出候选实现（Spec-First TDD）
- `/verifier`：调用 verification skill 作为机器证据，做验收/选优/驱动 fix-only grind

### 动态写入（每一步都要更新）

每次 subagent 调用后都必须追加写入：

- `SUMMARY.md`：高层可读运行日志（phase/task_id/结果/下一步）
- `PROGRESS.md`：
  - `## 子任务清单（PR 粒度）`：每个 task 的状态/更新时间/验收证据
  - `## 时间线（实时日志）`：每次调用的事件流水（**系统时间精确到秒** + subagent + 做了什么/结果/下一步）

为保证格式稳定一致（不依赖模型“随手写”），建议使用脚本写入：

```powershell
.\.cursor\scripts\upsert-task.ps1 -TaskId "T1" -Desc "实现 XXX" -Risk medium -Status IN_PROGRESS
.\.cursor\scripts\log-event.ps1 -Subagent planner -Phase plan -What "拆分大任务" -Result "生成 5 个子任务" -Next "开始实现第 1 个"
```

### 防止“todo 没做完就结束”

项目规则包含完成门禁：只要存在任何 task 不是 PASS 且不是 BLOCKED，就不允许结束；若受限无法继续，必须输出可复制粘贴的 `RESUME_PROMPT`，并把 next_action 同步写入 `SUMMARY.md/PROGRESS.md`。

## 为什么 Settings 里只看到 User Rule，而看不到项目 Rules？

官方文档区分了多种规则，其中项目级规则是 **Project Rules**，存放在 `.cursor/rules`，并应在 Settings 的 Project Rules 区域显示：[`Rules | Cursor Docs`](https://cursor.com/docs/context/rules)。

本仓库的项目规则使用 `.mdc`（带 frontmatter），更利于在 Settings 中展示与配置。

排查清单：

- 确保你是“打开项目根目录”而不是只打开某个子目录
- 在 `Cursor Settings → Rules` 里展开 **Project Rules**
- 仍不显示时，Reload Window / 重启 Cursor

## 仓库结构（示例）

- `template-cursor/`：可复制到任意项目的模板
- `.cursor/`：本仓库自用的 Cursor 配置（与 template 同步）
- `Makefile` / `tests/`：用于演示 `make check` 的最小可运行示例
- `PROGRESS.md` / `SUMMARY.md`：外部化记忆与验收证据

