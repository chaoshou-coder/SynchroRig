# Verifier ToDo

## 目标

让 `/verifier` 成为严格门禁：以机器证据为准验收，并在多候选实现时做正确选优；通过后记录到 `PROGRESS.md`。

## 现状

已更新 `.cursor/agents/verifier.md`：
- 强制调用 verification skill（脚本）
- strict JSON verdict
- PASS 时写入 `PROGRESS.md`（含 `All checks passed!` 证据）

## 待做

- 测试在真实多候选实现输入下，是否能稳定：
  - 选出最小改动且通过检查的候选
  - 输出可执行的 issue 列表驱动 fix-only
- 明确 grind 早停策略（建议在 verifier prompt 中增加）：
  - 连续 N 次失败且属于同类错误 -> 请求 sub-tasking

