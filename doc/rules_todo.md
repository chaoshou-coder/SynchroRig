# Rules ToDo

## 目标

补齐 `.cursor/rules/` 下的规则，并验证在实际使用中对各 subagent 生效。

## 已完成

- `granularity.mdc`：PR 粒度与风险分类
- `tdd.mdc`：Spec-First TDD 强制流程
- `memory.mdc`：外部化记忆与证据格式

## 待做

- 验证 Rules 加载后在 Cursor 的各 subagent 中均可见（planner/implementers/verifier/orchestrator）。
- 若 Cursor 环境中 rules 不自动生效：在各 agent prompt 顶部显式引用关键规则要点（最小重复）。

