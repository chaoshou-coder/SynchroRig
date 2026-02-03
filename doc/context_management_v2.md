# 上下文管理 V2：不进入明显退化区（Progressive Disclosure + Repo Map + 预算器）

> 目标：让每个 subagent 的注入上下文**始终低于明显退化区**，同时还能做复杂任务；避免“把所有文件/日志塞进上下文”的重复造轮子。

本方案直接复用/借鉴以下成熟实践（不复制其代码）：
- **Progressive disclosure（逐级展开）**：Claude-Mem 的 3 层检索协议 `search → timeline → get_observations`（先索引、后缩略上下文、最后按需取全文），实现 ~10x token 节省。参考：[`thedotmack/claude-mem`](https://github.com/thedotmack/claude-mem)
- **Repo map（仓库骨架）**：Aider 用 tree-sitter 提取符号/签名，并在 token 预算内动态选择最相关部分。参考：[`aider` Repository map](https://aider.chat/docs/repomap.html)
- **自动摘要/裁剪**：LangGraph/LlamaIndex 的 memory/summarization 组件证明“超过阈值就摘要/裁剪”是标准做法。参考：[`LangGraph memory`](https://docs.langchain.com/oss/python/langgraph/memory)、[`LlamaIndex memory`](https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/memory/)

---

## 0. 一句话结论（你照着做就行）

把当前 `.cursor/skills/context-rag/scripts/run-context-rag.ps1` 从“截断拼接 SUMMARY/PROGRESS”升级为：

1) **Budgeter**：按 subagent/profile 计算预算（tokens_approx），超预算时强制降级  
2) **Repo map**：常驻小骨架（签名/符号），不注入全文件  
3) **Progressive disclosure**：默认只注入“索引（IDs）”，只有需要时才展开 timeline/detail

---

## 1. 术语与不变约束

### 1.1 “不进入明显退化区”如何落地

- 你要控制的是：**注入给模型的动态上下文（context_payload）长度**，而不是项目规模。
- 执行层面：对每个 subagent，设一个 **budget_tokens**（保守上限），并强制：
  - `tokens_approx(context_payload) <= budget_tokens`
  - 若超预算：先降级（index-only / repo-map-only），再摘要，再少量 detail 拉取（永远不直接塞全文日志/全文件）

### 1.2 你现有实现的问题（必须改）

现 `run-context-rag.ps1` 只是对 `SUMMARY.md/PROGRESS.md` 做字符截断拼接：
- 不相关内容占满预算
- chars ≠ tokens（在不同语言/编码下误差很大）
- 不能按需展开（没有 ID、没有分层检索）

---

## 2. V2 架构（必须按三层实现）

### 2.1 三层检索协议（强制）

> 复用 Claude-Mem 的形状：先索引，再局部，再全文。不要一上来喂全文。

#### Layer 1：`index`（默认注入）
- 输出：紧凑索引（每条 1 行），带稳定 ID（整数或短 hash）
- 每条至少包含：`id`、`type`、`task_id`、`time`、`summary`（<=120 chars）、`refs`（可选：文件路径/检查命令）
- 预算：优先控制在 300–1200 tokens（视 subagent 而定）

#### Layer 2：`timeline`（仅当 index 不够时）
- 输入：`task_id` 或 `id`
- 输出：该 id 前后 N 条索引（仍然是索引行，不是全文）
- 预算：<= 800 tokens（建议）

#### Layer 3：`detail`（仅当需要高保真证据时）
- 输入：`ids=[...]`
- 输出：对每个 id 给“详细块”（最多 500–1500 tokens/条，批量时更严格）
- 规则：**先筛选 IDs 再拉 detail**，永远不要直接把 PROGRESS/SUMMARY 全文塞进上下文

### 2.2 Repo Map（骨架层）

> 复用 Aider repo map 思路：提供“全局 API/符号地图”，让 agent 能点名要看哪段代码。

最小可行实现（MVP）：
- 只做 Python：扫描 `synchrorig/` 与 `.cursor/`（可扩展）
- 输出：每个文件列出：
  - 顶层函数/类名
  - 函数签名（能取就取）
  - docstring 第一行（可选）
- 预算：固定 `map_tokens`（例如 800–1500 tokens）

---

## 3. 数据来源（不要再读全文件）

### 3.1 “观察（observations）”的来源建议

你不需要引入 claude-mem 的整套插件，只需要复用其“observations + IDs”概念：

- **事件源**：
  - `PROGRESS.md` 的时间线（event rows）
  - `SUMMARY.md` 的运行日志（可选）
  - `runs/` 下的 task JSON（高信号）
  - （可选）终端输出的关键片段（建议只存错误摘要 + 命令 + exit_code）

建议新增一个“机器友好”的观测存储（任选其一）：

- 方案 A（最简单）：`runs/memory/observations.jsonl`（一行一个 JSON，带自增 id）
- 方案 B（更稳）：SQLite（`runs/memory/mem.db`），用 `sqlite3` 内置库即可

---

## 4. 配置（必须新增一份明确预算）

新增：`.cursor/skills/context-rag/config.json`（不要只用 example）

最少包含：
- 每个 profile/subagent 的 `budget_tokens`（动态上下文上限）
- `index_tokens` / `timeline_tokens` / `detail_tokens` / `map_tokens`
- `max_per_source_tokens`（可选）

说明：不要给 gpt-5.2 直接开到 256k；你的目标是“不进退化区”，应保守。

---

## 5. 需要改哪些文件（照着清单做）

### 5.1 修改（必改）

1. `.cursor/skills/context-rag/scripts/run-context-rag.ps1`
   - 增加参数：`-Mode index|timeline|detail|map`、`-Query`、`-TaskId`、`-Ids`、`-Profile`
   - 输出：**只输出 context_payload**（文本或 JSON 都行，但要稳定）
   - 内部实现：按预算器拼装 payload；默认 Mode=index

2. `.cursor/skills/context-rag/SKILL.md`
   - 更新契约：说明 Mode、IDs 的逐级展开机制；强调“不允许全文拼接”

3. `.cursor/agents/orchestrator.md`（以及你们的编排规则）
   - 在调用 implementers/verifier 前：先跑 context-rag（现有）但传 `-Mode index`；只有当 implementer/verifier 明确要求时才跑 `timeline/detail`

### 5.2 新增（推荐）

4. `.cursor/skills/context-rag/scripts/build-repo-map.py`
   - 生成 repo map（Python-only MVP）

5. `runs/memory/observations.jsonl`（或 SQLite）
   - 由脚本/工具写入（不要求手写）

6. `tests/test_context_rag_progressive_disclosure.py`
   - 门禁：验证 run-context-rag 的输出模式与预算不超标（至少校验 chars 或 tokens_approx）

---

## 6. 验收标准（你按这几条就知道做完没）

1) `run-context-rag.ps1 -Mode index ...` 输出中：
- 每条索引行都有稳定 ID
- 总长度不超过 `index_tokens` 对应的预算（至少做到 chars 上限 + tokens_approx 记录）

2) `-Mode detail -Ids ...`：
- 只返回指定 IDs 的 detail
- detail 预算可控（单条不超过 `detail_tokens`）

3) Orchestrator 流程：
- 默认只注入 index + repo map（可选）
- 只有明确请求才展开 timeline/detail

4) `make check` 通过（ruff + pytest）

---

## 7. 迁移策略（避免一次性大改）

建议按 3 个 PR-sized 步骤落地：

PR1（最小可用）：给 context-rag 增加 `-Mode index`，先做到“索引输出 + 预算器（粗略 tokens_approx）”，并在 orchestrator 默认只用 index  
PR2：加入 `timeline/detail` + observations 存储（jsonl/SQLite），并加 pytest 门禁  
PR3：加入 repo map（Python MVP），并把 planner/orchestrator 也改为骨架优先

