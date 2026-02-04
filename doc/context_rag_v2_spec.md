# Spec：Context‑RAG V2 可替换后端架构（瀑布式）

> 目标：**定协议，不定实现**。把 observations / repo_map / budgeter 都变成可替换后端；用 JSONL/SQLite 做唯一 source of truth；Markdown 只做 append-only 展示；把精力放在 Cursor 集成与阈值配置上。
>
> 适用范围：本仓库的 `.cursor/skills/context-rag/` 及其 runner，面向 orchestrator 在调用 subagent 前生成 `context_payload` 的流程。

## 1. 背景与问题定义

### 1.1 背景

当前上下文供给与运行记录存在两类风险：

- **真源不结构化**：把 `SUMMARY.md/PROGRESS.md` 的文本/表格当作事实源，会导致格式漂移、噪声注入、难以精确检索与预算控制。
- **实现耦合**：将“存储/检索/预算/拼装/输出格式”混在 runner 中，会使任何小改动都变成不可回滚的大改动。

### 1.2 目标（Goals）

- **G1：定协议，不定实现**：后端可替换（observations / repo_map / budgeter），上层契约稳定。
- **G2：真源结构化**：JSONL/SQLite 为唯一 SoT；Markdown 仅展示（append-only），不参与检索。
- **G3：Progressive disclosure**：默认 `index`，按需 `timeline`，最后 `detail`；禁止一上来全文拼接。
- **G4：Repo map**：提供仓库骨架（符号/签名），在预算内做裁剪/选择；重要性排序可后置。
- **G5：预算可证**：任何输出都必须有预算字段，且可用自动化测试验证“未超预算 / 触发降级”。
- **G6：可回滚**：所有新能力都必须受 feature flags 控制，出问题可一键切回旧路径。

### 1.3 非目标（Non-Goals）

- 不做完整 Web UI（另开子项目）。
- 不把模型选择/提示词策略写死在后端实现（属于 orchestrator 策略层）。
- 不在 MVP 阶段实现依赖图 ranking（仅预留接口）。

## 2. 冻结决策（Decisions Freeze）

以下决策一经冻结，后续 PR 不得随意变更；如需变更，必须新开 Spec 版本并明确迁移/回滚策略。

1. **SoT（唯一真源）**：`runs/memory/observations.jsonl`（先 JSONL；SQLite 作为后续增强）。
2. **Markdown 的角色**：仅 append-only 展示；**严禁**作为检索真源。
3. **Observation `id`**：自增 `int`（便于排序与 timeline window；并发写入通过“单写入点/文件锁”解决）。
4. **Repo map MVP**：符号/签名抽取 + 预算裁剪（限额）；**不实现**重要性排序（ranking 后置）。
5. **兼容/回滚**：保留 `observations_backend=markdown` 作为**应急** fallback（默认关闭；出事一键切回）。
6. **输出协议**：`context_payload` 统一 JSON，stdout 只输出 payload，不混日志。

## 3. 总体架构与职责边界（解耦）

### 3.1 组件划分

- **Runner（`run-context-rag.ps1` / `.sh`）**
  - 职责：解析参数、加载配置、选择后端、调用 Python CLI/模块、将 payload 原样输出到 stdout。
  - 禁止：在 runner 中实现“存储/排序/拼装”等业务逻辑。

- **Budgeter（可替换）**
  - 职责：根据 profile/subagent/mode/scope 计算预算与降级策略阈值。

- **ObservationStore（可替换）**
  - 职责：写入结构化 observations；提供 `index/timeline/detail` 查询。
  - 实现：JSONL（优先）→ SQLite（增强）。

- **RepoMapProvider（可替换）**
  - 职责：生成 repo map（符号/签名骨架）；支持预算内裁剪/选择（MVP 可先限额裁剪）。

- **ContextAssembler（稳定）**
  - 职责：按预算拼装 `task_json + observations + repo_map`，生成最终 `context_payload`；执行降级策略。

- **Markdown 展示层（append-only）**
  - 由 orchestrator 通过脚本追加写入（如 `log-event.ps1` / `progress_tools.py`）。
  - 不参与检索与预算控制。

### 3.2 数据流（简化）

1) orchestrator 在调用 subagent 前 → 调用 context-rag runner  
2) runner → 调用 Python 后端 → 读/写 observations SoT、读取 repo map cache（如有）  
3) Budgeter 给出预算 → ContextAssembler 按 `mode` 拼装 payload → stdout 输出 JSON  
4) orchestrator 把子代理一行日志通过脚本追加写入 Markdown（展示层）  

## 4. 核心协议（必须稳定/版本化）

### 4.1 `context_payload`（对 subagent 注入的最终输出）

**格式**：JSON（单对象），必须包含以下字段：

- `version`: `"context_payload.v2"`
- `generated_at`: `YYYY-MM-DD HH:mm:ss`
- `subagent_type`: `orchestrator|planner|implementers|verifier|consultant`
- `mode`: `index|timeline|detail|map|mixed`
- `budget`:
  - `budget_tokens`: int
  - `tokens_approx`: int
  - `truncated`: bool
  - `downgrade_applied`: string[]（记录降级链路，如 `["detail→timeline", "timeline→index"]`）
- `task`:
  - `task_id`（可选）
  - `task_json`（可选；建议只放摘要或路径，不直接塞大 JSON）
- `observations`:
  - `source`: `"jsonl"|"sqlite"|"markdown_fallback"`
  - `items`: array（index/timeline/detail 返回的条目）
- `repo_map`:
  - `source`: provider 名称
  - `items`: array
- `notes`: string[]（短提示，例如“默认 index-only；要 detail 请给 ids”）

**约束**

- stdout 只允许输出此 JSON；任何日志必须写 stderr 或文件。
- payload 必须可被 `json.loads` 解析；字段缺失视为 breaking change。

### 4.2 Observation schema（结构化真源）

**Observation 记录（JSONL 每行 / SQLite 一行）必须包含：**

- `schema_version`: `"obs.v1"`
- `id`: int（自增，稳定 ID）
- `ts`: string（`YYYY-MM-DD HH:mm:ss`）
- `task_id`: string（可空）
- `actor`: `orchestrator|planner|implementers|verifier|skill|system`
- `phase`: `plan|implement|verify|fix|other|task`
- `summary`: string（<=120 chars；用于 index）
- `detail`: string（可选；用于 detail，长度上限由预算器控制）
- `refs`: object（可选）
  - `files`: string[]
  - `commands`: string[]
  - `urls`: string[]

**写入规则**

- append-only；禁止原地修改/重排。
- Markdown 只展示 `summary`（可带极短证据片段），不写全 detail。

### 4.3 Repo map schema（骨架）

**RepoMapItem（MVP）字段：**

- `schema_version`: `"repomap.v1"`
- `path`: string
- `hash`: string（文件内容 hash 或 map 生成 hash）
- `symbols`: array
  - `kind`: `class|function|method|const|var|module|other`
  - `name`: string
  - `signature`: string（可选）
  - `line_start`: int（可选）
  - `line_end`: int（可选）

## 5. 可替换后端接口契约（Contracts）

### 5.1 ObservationStore（可替换后端 contract）

- `append(observation) -> id`
- `index(query?, filters?, limit, budget_tokens) -> ObservationIndexItem[]`
- `timeline(task_id, window, budget_tokens) -> ObservationIndexItem[]`
- `detail(ids[], budget_tokens) -> ObservationDetailItem[]`

**后端实现 A：JSONL（MVP）**

- 路径：`runs/memory/observations.jsonl`
- 索引：MVP 允许线性扫描；后续可加缓存/倒排（不改变接口）。

**后端实现 B：SQLite（增强）**

- 路径：`runs/memory/mem.db`
- 可选：FTS5/索引字段（后置）。

**应急回滚**

- `observations_backend=markdown`：切回旧逻辑（仅作为应急 fallback；默认关闭）。

### 5.2 RepoMapProvider（可替换 + 可降级）

- `build(scope_paths, include_globs, exclude_globs, out_path, budget_tokens, profile) -> RepoMap`
- `load(out_path) -> RepoMap`
- `select(repo_map, query, budget_tokens) -> RepoMap`

**重要性排序（后置增强）**

借鉴 Aider 的思路：构建依赖图并做 ranking，再在 token budget 内裁剪。MVP 阶段只做“限额裁剪”，但必须保留 `select()` 接口与配置项，避免未来 breaking。

### 5.3 Budgeter（硬约束）

- 输入：`subagent_type`, `profile`, `mode`, `scope`, `model_id(optional)`
- 输出：`budget_tokens`、分源配额、top_k、降级链路。

**预算估算（MVP）**

- `tokens_approx = ceil(chars/4)`（仅用于门禁与降级；后续可替换更准确 tokenizer，不改变接口）。

## 6. 配置（Config）与 Feature Flags（回滚开关）

配置文件：`.cursor/skills/context-rag/config.json`（必须存在；不只依赖 example）。

### 6.1 必需配置项

- `profiles[profile].budgets.{index_tokens,timeline_tokens,detail_tokens,map_tokens}`
- `profiles[profile].max_per_source_tokens.{observations,repo_map,task_json}`
- `profiles[profile].top_k.{index,timeline,detail}`
- `profiles[profile].downgrade_order`: `["index","map","timeline","detail"]`

### 6.2 Feature flags（必须）

- `flags.use_observations_store`（默认 false → 灰度打开）
- `flags.observations_backend`: `markdown|jsonl|sqlite`
- `flags.use_repo_map`（默认 false）
- `flags.repo_map_provider`: `python_mvp|...`
- `flags.use_progressive_disclosure`（默认 true，但允许关闭回到 index-only）

## 7. Runner/CLI 约定（执行面契约）

Runner 参数（可选从 env 读取，但参数名/语义固定）：

- `-Mode index|timeline|detail|map`
- `-TaskId <id>`（可选）
- `-Ids <id1,id2,...>`（detail）
- `-Query <text>`（可选）
- `-Profile <name>`（可选）
- `-SubagentType <type>`
- `-TaskJsonPath <path>`（可选）
- `-Scope <csv>`（如 `progress,summary,task,codebase`；最终由后端解释）

stdout：

- 只输出 `context_payload` JSON（无其他文本）。

stderr / 文件：

- 可输出诊断信息（例如“降级原因”），但不得污染 stdout。

## 8. 里程碑（瀑布式 PR 顺序）

每个里程碑（PR）都必须：`make check` 全绿 + 有回滚开关 + 新增/更新最小 pytest 门禁。

### 8.0 PR 顺序（执行版清单）

> 说明：以下为可直接照抄执行的 PR 清单（原子化、互解耦、可回滚）。与本章后续 PR-1..PR-6 的结构化描述一致；如两者出现冲突，以此清单为准并同步修订文档。

- 瀑布式里程碑 / PR 顺序（原子化、互解耦、可回滚）
- 每个 PR 都必须：make check 全绿 + 配置开关可回滚。
- PR-1（协议先行：定协议不定实现）
  - 交付：context_payload.v2 JSON schema + config.json flags/budgets 结构
  - 验收：runner 能输出可解析 JSON，含 version/budget/mode/subagent_type
  - 回滚开关：flags.use_context_payload_v2=false（或保持旧输出并行）
- PR-2（ObservationStore JSONL：写入 + index）
  - 交付：JSONL writer + index()（query 可先 no-op）
  - 验收：能 append；-Mode index 输出 items 且受预算约束
  - 回滚开关：observations_backend=markdown
- PR-3（progressive disclosure：timeline/detail 按 task_id/ids）
  - 交付：timeline(task_id)、detail(ids[])（只按 ids 拉 detail）
  - 验收：detail 只返回指定 ids；超预算自动降级到 index
  - 回滚开关：flags.use_progressive_disclosure=false（退回 index-only）
- PR-4（Repo map MVP：build + cache + load）
  - 交付：repo map builder（Python-only）+ 缓存文件（带版本/哈希）
  - 验收：-Mode map 输出 repomap schema；预算裁剪按限额生效
  - 回滚开关：flags.use_repo_map=false
- PR-5（拼装器固化：混合输出 + 降级链路）
  - 交付：ContextAssembler（index + 可选 map；明确请求才 timeline/detail）
  - 验收：任何组合不超预算；降级链路可测试
  - 回滚开关：downgrade_order 配置 + 关闭 map/detail
- PR-6（可选增强：重要性排序 / SQLite）
  - 交付：依赖图 ranking（借鉴 Aider 思路）或 SQLite + FTS
  - 验收：同一 query 下 map 选择更相关/更稳定；性能指标达标
  - 回滚开关：repo_map_selector=simple_limit / observations_backend=jsonl

置信度：8/10（方案与现有目标一致；最大风险在“自增 ID 的并发写入”和“markdown 真源残留诱惑”，但都有开关可回滚）。

### PR-1：协议先行（定协议不定实现）

- **交付**：
  - `context_payload.v2` schema 文档化（本 spec）
  - `config.json` flags/budgets 结构落地
  - runner 输出稳定 JSON（可用 mock store/provider）
- **验收**：
  - `-Mode index` 输出可解析 JSON，包含 `version/budget/mode/subagent_type`
- **回滚**：
  - `flags.use_context_payload_v2=false`（如需要保留旧输出并行）

### PR-2：ObservationStore JSONL（append + index）

- **交付**：JSONL 写入 + `index()`
- **验收**：
  - 能 append observation
  - `-Mode index` 输出 items，且 `tokens_approx <= budget_tokens`
- **回滚**：`observations_backend=markdown`

### PR-3：Progressive disclosure（timeline/detail）

- **交付**：`timeline(task_id)`、`detail(ids[])`
- **验收**：
  - detail 只返回指定 ids
  - 超预算自动降级至 timeline/index（并在 `downgrade_applied` 记录）
- **回滚**：
  - `flags.use_progressive_disclosure=false`（退回 index-only）

### PR-4：Repo map MVP（build + cache + load）

- **交付**：Python-only repo map builder + cache（带版本/哈希）
- **验收**：
  - `-Mode map` 输出 repomap schema
  - 按预算限额裁剪生效
- **回滚**：`flags.use_repo_map=false`

### PR-5：ContextAssembler 固化（mixed + 降级链路）

- **交付**：index + 可选 map 的默认拼装；仅在明确请求时展开 timeline/detail
- **验收**：所有组合不超预算；降级链路可测试
- **回滚**：关闭 map/detail 或调整 `downgrade_order`

### PR-6（可选增强）：重要性排序 / SQLite

- **交付**：
  - 依赖图 ranking（借鉴 Aider 思路）或 SQLite + FTS
- **验收**：相关性更稳定或性能达标（需定义指标）
- **回滚**：
  - `repo_map_selector=simple_limit`
  - `observations_backend=jsonl`

## 9. 验收标准（机器可证）

### 9.1 正确性

- `-Mode index`：输出含 `version/mode/budget/observations.items[]`，且不超预算
- `-Mode detail -Ids ...`：只返回指定 ids 的 detail
- `-Mode map`：输出 repomap schema，受 `map_tokens` 约束

### 9.2 可回滚

- 切换任意 `flags.*` 后，runner 不 crash，stdout 仍输出可解析 JSON

### 9.3 不退化（预算门禁）

- pytest 校验：`tokens_approx <= budget_tokens`
- 如超预算：必须触发降级，并在 `downgrade_applied` 中体现

### 9.4 可替换

- 同一组测试可在 `jsonl` 与 `sqlite` backend 下跑通（SQLite 可后置）

## 10. 风险与对策

- **并发写入 JSONL**：若多进程写入，必须引入文件锁或“单写入点”（orchestrator 脚本统一写入）。
- **协议漂移**：任何字段变更必须走 `version` 升级与兼容期，禁止暗改。
- **Markdown 诱惑**：一旦再次把 Markdown 当真源，长期成本会指数上升；必须在代码审查与测试中禁止。

