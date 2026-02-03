# Planner ToDo

## 目标

让 `/planner` 稳定输出 PR-sized 的任务列表（strict JSON），包含风险分类与动态并行数建议。

## 现状

`.cursor/agents/planner.md` 已包含：
- PR 粒度约束
- 风险分类（low/medium/high）与并行数建议
- strict JSON 输出结构

## 待做

- 在 3–5 个不同类型需求上试跑，检查：
  - 任务 LOC 是否稳定落在 100–300（极少超过 400）
  - 是否能在需要时触发 `sub_tasking_needed`
- 若发现经常超范围：
  - 强化“垂直切片（可验证）优先”的分解提示
  - 明确“接口变更/新依赖/跨模块”必定提升风险等级

