## 背景与目标（稳定性/质量优先）

SynchroRig 的“激进路线”不是业务应用，而是把 Cursor 工作流本身产品化：以 **并行候选实现**、**强契约验证门禁**、**可插拔的 skills/commands**、**结构化证据**、**外部化记忆** 为核心，面向 Windows + Linux 的一致执行入口，优先追求稳定性、可复现性与质量。

本路线以仓库现有结构为基座（`.cursor/`、`template-cursor/`、`Makefile`、`tests/`、`run-check.ps1/.sh`、`context-rag` skill、`SUMMARY.md/PROGRESS.md`），并显式引入：
- **git + git worktree** 作为并行隔离的硬前提（worktrees_now）
- **per_workspace 日志**：每个 worktree/候选写独立日志；Orchestrator 汇总生成根 `PROGRESS.md/SUMMARY.md`
- **structured check_contract**：`run-check` 提供 fast/strict + JSON 输出；Verifier 以 JSON 为准，人类可读仅摘要

---

## Non-goals（哪些不做）

- 不构建业务功能、业务 UI、业务 API。
- 不将 `make` 作为跨平台硬依赖；Windows 上不要求安装 GNU Make。
- 不在门禁命令中执行自动修复（`check` 只读）；修复属于显式 `fix/fmt` 命令。
- 不依赖“聊天记录”作为事实来源；事实以 artifacts + JSON evidence + 外部化日志为准。
- 不在 hooks 中默认执行会写入工作区/索引的动作（除非用户显式开启“可写 hooks”模式）。

---

## 核心抽象/契约（task schema、artifacts、evidence、phase、retry 语义）

### 1) Task（Planner 输出的任务契约）

**Task JSON Schema（概念级，供实现对齐）**
- `id`：稳定可引用（例：`T-2026-02-02-001`）
- `title`：一句话标题
- `description`：做什么 + 为什么（单意图）
- `risk`：`low|medium|high`
- `parallel_count`：候选并行数（建议：low=1, medium=2, high=3–5）
- `acceptance`：
  - `commands`：至少包含 `run-check --mode strict --format json`
  - `criteria`：通过条件（以 JSON evidence 为准）
- `estimated_loc`：预估 LOC（目标 100–300，硬上限 400）
- `files_involved`：预计改动文件（硬上限 10）
- `public_contracts_touched`：公开接口/契约变更（无则 `N/A`）

### 2) Phase（状态机阶段）

- `plan`：产出 Task 列表（严格 JSON）
- `implement`：按 Task 在隔离 worktree 中执行 Spec-First TDD（先红后绿）
- `verify`：只读门禁（strict），Verifier 以 JSON evidence 判定 PASS/FAIL
- `fix`：仅针对 verifier issues 的最小修复（仍遵循 TDD）
- `subtask`：任务超界或歧义触发拆分（重新回到 plan）

### 3) Artifacts（产物）

每个候选实现（candidate）必须产生可审计产物（建议放在该 worktree 内 `runs/<task_id>/<candidate_id>/`）：
- `task.json`：任务契约快照
- `run-check.json`：结构化验证证据（fast/strict 均可）
- `run-check.txt`：人类可读摘要（可选）
- `tdd.log`：测试红/绿过程关键输出摘要（可选，但推荐）
- `changeset.txt`：变更文件清单与统计（可选）
- `notes.md`：候选差异点/关键决策（可选）

### 4) Evidence（证据与判定）

**唯一裁决输入**：`run-check --mode strict --format json` 的输出（文件或 stdout）。
- PASS 必须包含 `summary.all_checks_passed = true` 且 `summary.banner = "All checks passed!"`
- FAIL 必须包含失败分类与可定位信息（测试/格式/静态检查/契约校验等）

### 5) Retry（重试语义）

- 同一失败点定义：`task_id + phase(verify/fix) + subagent`
- 每个失败点最多重试 3 次；每次必须记录 `retry_count` 与最新 evidence 摘要
- 仍失败则：触发 `subtask` 或标记 `BLOCKED`（缺少外部信息/权限/环境）

---

## 目录结构建议（现有 + 激进路线新增的目录/文件）

### 现有（必须保留并对齐）

- `.cursor/`：规则、agents、skills、脚本（含 init-big-task、context-rag、verification、compression）
- `template-cursor/`：工作流模板/脚手架
- `tests/`：pytest（Spec-First TDD 起点）
- `Makefile`：可选前端（Linux/WSL/有 make 时便利）
- `run-check.ps1` / `run-check.sh`：跨平台一致入口（真入口）
- `SUMMARY.md` / `PROGRESS.md`：外部化记忆（根汇总）

### 新增（激进路线建议）

- `doc/aggressive_architecture.md`：本文档
- `doc/lessons/`：自我改进记录（可加载、可检索）
- `scripts/`：
  - `worktree/`：worktree 管理脚本（create/list/cleanup/lock）
  - `evidence/`：证据收集与规范化（合并 JSON、摘要生成）
- `hooks/`：建议的 git hooks 模板（只读/可写分离）
- `runs/`：根汇总视角的运行索引（仅聚合，不直接写候选日志）
- `workspaces/`：可选（若需约定 worktree 放置目录）
- `audits/`：安全审计/执行记录（可选）

---

## 执行流（从大任务到验证通过的状态机；含 plan->implement->verify->fix->subtask）

### 0) 预备：git 化与远端策略（worktrees_now 硬前提）

前置条件：
- 仓库必须是 git repo（`git init` 或 clone）
- 推荐配置远端 `origin`（团队协作与 CI 必需）
- 推荐默认分支：`main`（或 `master`，需统一）

分支命名建议（避免候选互相污染）：
- 任务主分支：`aggr/task/<task_id>`
- 候选分支：`aggr/task/<task_id>/c<k>`（k 从 1..N）
- 合并策略：**只合并最终被 verifier PASS 的候选**；其余候选分支与 worktree 清理

### 1) plan

输入：用户大任务需求  
输出：Planner 严格 JSON tasks（每个 task 为 PR 粒度）

产物（根）：
- `SUMMARY.md/PROGRESS.md` 初始化并记录 big_task 元信息（通过现有 `init-big-task` 脚本）
- `runs/<big_task_id>/plan.json`（可选）

### 2) implement（并行候选）

对每个 task：
- Orchestrator 先调用 `context-rag` 获取最小上下文 payload
- 按 `parallel_count` 创建 N 个候选 worktree（每个 worktree 独立执行 TDD 与产物写入）
- 每个候选必须：
  - 新增/修改 `tests/`（先红）
  - 运行 test 证明确实失败（red）
  - 最小实现变绿（green）
  - 生成 `run-check`（至少 fast；strict 可留给 verifier，但建议候选先自检 strict）

### 3) verify（只读门禁）

Verifier 在**选定候选**（或逐个候选）上执行：
- `run-check --mode strict --format json`
- 以 JSON evidence 判定 PASS/FAIL
- PASS：进入下一 task
- FAIL：输出 issues，进入 fix

### 4) fix

Implementers 在同一候选 worktree 中：
- 仅针对 verifier issues 修复（不扩 scope）
- 仍遵循 TDD（必要时补测试先红后绿）
- 生成新的 `run-check` evidence

然后回到 verify。

### 5) subtask（拆分）

触发条件：
- 预计/实际改动 > 10 文件 或 > 400 LOC
- 验收标准无法用测试/strict check 表达
- 连续失败且无法收敛（需求歧义或跨模块过大）

动作：
- Orchestrator 调用 Planner 拆分并替换 task 列表
- 重新进入 plan -> implement

---

## 并行策略（worktrees：命名、隔离、合并、清理）

### worktree 放置与命名

推荐统一根目录外侧放置（避免污染主工作区）：
- 目录：`../SynchroRig.wt/<task_id>/c<k>/`
- 分支：`aggr/task/<task_id>/c<k>`

隔离原则：
- 每个 worktree **只写自己的 per_workspace 日志与 artifacts**
- 根工作区只做 **汇总**（由 orchestrator 生成/更新），不参与候选并发写

### 合并与选择

- 默认策略：先跑 fast 再 strict；strict PASS 的候选才允许进入合并路径
- 合并建议：`--no-ff` 或 squash（团队统一即可）；关键是证据链可追溯（保留 `run-check.json` 索引）

### 清理

- PASS 候选合并后：移除其 worktree；保留必要 evidence 索引（根 `runs/`）
- FAIL/淘汰候选：移除 worktree + 删除候选分支
- 强制清理前：检查无未提交更改（避免丢失证据）；证据应已写入 `runs/<task_id>/...`

---

## 验证与门禁分层（fast/strict；只读 vs 修复命令）

### 分层目标

- **fast**：开发者反馈回路（快、覆盖关键失败类型）
- **strict**：验收门禁（完整、可复现、稳定）

### 只读门禁（明确要求 1）

- `run-check`：只读，不修改工作区、不自动修复、不写回格式化结果  
  输出结构化 JSON evidence（structured contract）
- `fix/fmt`：独立命令，显式触发，可能写入工作区（与门禁分离）

### Windows 无 make 的一致入口（明确要求 2）

- Windows：以 `run-check.ps1` 为真入口；`Makefile` 只是可选薄前端
- Linux/macOS：`run-check.sh` 为真入口；`Makefile` 可调用它，但不能反向依赖 make

### `run-check` 强契约（structured）

建议 CLI：
- `run-check --mode fast|strict --format json|text [--out <path>] [--worktree <path>] [--task <task.json>]`

退出码建议：
- `0`：PASS（strict/fast 均适用）
- `1`：FAIL（存在失败项）
- `2`：ERROR（环境/依赖/脚本错误，非业务失败）

JSON 输出建议字段：
- `meta`：`timestamp`, `platform`, `cwd`, `git`(commit, branch, dirty)
- `mode`：`fast|strict`
- `summary`：`all_checks_passed`（bool）, `banner`（严格要求包含/匹配 `"All checks passed!"`）, `duration_ms`
- `checks[]`：每项 `name`, `status(pass|fail|error|skip)`, `command`, `stdout_excerpt`, `stderr_excerpt`, `artifacts[]`
- `diagnostics[]`：可定位信息（文件/行/规则/建议）
- `contracts`：公开契约校验结果（若有）

---

## hooks/commands/skills 的最小集合（建议列表 + 触发时机）

### Commands（仓库脚本/入口）

- `run-check`（ps1/sh）：**唯一门禁入口**（fast/strict + JSON）
- `run-fix`（ps1/sh）：显式修复（例如自动修复 lint/格式/生成文件），可写
- `run-fmt`（ps1/sh）：显式格式化，可写
- `scripts/worktree/create`：创建候选 worktrees（含分支命名约束）
- `scripts/worktree/cleanup`：清理 worktrees/分支/残留锁
- `scripts/evidence/collect`：收集候选 evidence，生成根索引
- `scripts/log/merge`：从 per_workspace 汇总到根 `PROGRESS.md/SUMMARY.md`（只读读取候选日志，根写入由 orchestrator 单点执行）

### Hooks（最小权限与时机，明确要求 6）

建议默认只启用只读 hooks：
- `pre-commit`（只读）：`run-check --mode fast --format json`（失败阻止提交）
- `pre-push`（只读）：可选 `run-check --mode strict --format json`（团队可选）

禁止默认启用：
- 自动 `fix/fmt` 的 hooks（会写工作区，破坏可预期性与审计）

审计与最小权限：
- hooks 只调用仓库内脚本（固定路径），禁止从网络拉取执行内容
- 脚本应打印自身版本/哈希（可选）与执行命令列表
- 对外部命令执行应白名单化（pytest、python、node 等），避免任意执行面扩大

### Skills（Cursor 内能力复用）

- `context-rag`：上下文检索与 payload 生成（见下节契约）
- `verification`：执行 strict 门禁（本质上应调用 `run-check --mode strict`）
- `compression`：把已验收内容压缩写入根 `SUMMARY.md`

---

## context 管理：iterative retrieval + context-rag skill 的契约（明确要求 4）

### 契约：何时调用

Orchestrator 在以下时机必须调用 `context-rag`：
- 进入每个 task 的 `implement` 之前（为 implementers 提供最小上下文）
- 进入 `verify` 之前（为 verifier 提供任务契约、证据位置、关键变更点）
- 进入 `fix` 之前（将 verifier issues + 相关上下文注入 implementers）

### 契约：输入

- `subagent_type`：`orchestrator|planner|implementers|verifier`
- `task_id`
- `task_json`：当前 task 的 JSON（或路径）
- `scope`：`progress|summary|task|code|tests|scripts`（可组合或枚举）
- `query`（可选）：本轮关注点（例如 “where is run-check implemented”）

### 契约：输出（context_payload）

- `context_payload`：
  - `files[]`：路径 + 摘要 + 关键片段（或行范围引用）
  - `artifacts[]`：相关 evidence/日志路径
  - `notes`：检索理由与覆盖面说明（短）
  - `budget`：上下文预算使用情况（可选）

### Iterative retrieval（迭代检索策略）

- 第一次：基于 task_json + 规则文件 + 最近证据索引做粗检索
- 第二次：基于失败/疑点（verifier issues）做定向补检索
- 目标：让每个 subagent 的输入上下文**可控、可解释、可复现**

---

## memory/log：PROGRESS/SUMMARY 的结构化、冲突与轮转策略（协作场景，明确要求 5）

### per_workspace（已选）写入规则

每个候选 worktree 写入独立日志（避免并发冲突）：
- `runs/<task_id>/c<k>/PROGRESS.md`（候选级，append-only）
- `runs/<task_id>/c<k>/SUMMARY.md`（候选级，append-only）
- `runs/<task_id>/c<k>/timeline.log`（可选，机器友好）

根日志（汇总视角）：
- 根 `PROGRESS.md` / `SUMMARY.md` 只允许 **Orchestrator 单点写入**
- 汇总来源：读取候选 worktree 的 per_workspace 日志与 `run-check.json`

### 汇总与冲突处理

- 冲突规避：候选不写根日志；根日志不在多个 worktree 并发编辑
- 汇总方式：以 `task_id/candidate_id` 为主键，生成确定性段落（可重复生成，幂等）
- 若必须协作：建议采用“根日志只在 main worktree 更新 + PR 合并”策略，避免手工冲突

### 轮转策略

- 每个 big task 完成后，将 `runs/<big_task_id>/` 归档（例如按日期目录）
- 根 `SUMMARY.md` 保持短（压缩后的工作记忆）；详细证据留在 `runs/` 下索引
- `PROGRESS.md` 可 append-only，但应按 `task_id` 分段，便于检索

---

## 自我改进与学习（lessons 机制：何时记录、格式、如何被加载）

### 何时记录

- strict FAIL 且原因具有模式性（环境/依赖/脚本/规则缺口）
- 同一失败点重试 ≥2 次
- 发生“规则冲突/边界突破/误用 hooks/证据不可复现”等流程缺陷

### 记录位置与格式

- `doc/lessons/YYYY-MM-DD_<topic>.md`（人类可读）
- 必须包含最小字段：
  - `symptom`：现象（可复现）
  - `root_cause`：根因
  - `fix`：如何修复
  - `prevention`：如何预防（规则/脚本/契约变更）
  - `evidence`：关联的 `run-check.json` 路径与摘要

### 如何被加载

- `context-rag` 的默认检索范围应包含 `doc/lessons/`
- Orchestrator 在 plan/verify/fix 前将相关 lesson 注入 payload（只注入相关主题）

---

## 可观测性与故障诊断（结构化输出、归因流程）

### 结构化输出（首选）

- 以 `run-check.json` 为主：可被 Verifier/CI/脚本解析
- 人类输出仅用于快速阅读，不作为裁决依据

### 归因流程（建议）

1. 先区分：`FAIL`（业务/测试/静态检查） vs `ERROR`（环境/脚本）
2. 定位失败 check：`checks[].name/status/diagnostics`
3. 若为环境：记录到 lessons，并补充 `run-check` 的 `meta` 字段（平台/依赖版本）
4. 若为测试：回到 TDD（补测试、最小修复、复跑 fast，再跑 strict）

---

## 演进路线（从现在到激进路线的里程碑）

- M0（现在）：统一入口存在（`run-check.ps1/.sh`）、`Makefile` 仅薄前端、tests 基于 pytest
- M1：定义并落地 `run-check` strong contract（fast/strict + JSON + 退出码）
- M2：git 化 + worktrees_now（脚本化创建/清理、分支命名约束）
- M3：per_workspace 日志落地；Orchestrator 汇总根 `PROGRESS.md/SUMMARY.md`（幂等合并）
- M4：lessons 机制落地并接入 context-rag（可检索、可注入）
- M5：hooks 最小集合固化（默认只读），安全审计与白名单执行完善
- M6：组件可插拔（checks 列表配置化、evidence 收集器可替换、CI 与本地一致）
