# Implementers ToDo

## 目标

让 `/implementers` 稳定遵守 Spec-First TDD：先红测试、再实现、最后 `make check` 全绿，并在并行候选时输出可比较的证据。

## 现状

`.cursor/agents/implementers.md` 已包含：
- Spec-First TDD 强制流程
- 要求执行 `make test`（红/绿）与 `make check`
- 并行候选标注（instance id）
- 任务超范围时 BLOCKED

## 待做

- 增加“fix-only”运行约定（由 orchestrator 传入 verifier 的 issues 列表）：
  - 只改动为修复 issue 所需的最小范围
  - 不扩展任务范围
- 约束输出更结构化（可选）：
  - 最终必须给出 `make check` 的关键片段（含 `All checks passed!`）

