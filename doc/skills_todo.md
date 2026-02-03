# Skills ToDo

## verification skill

### 目标

提供统一、可脚本化的 `make check` 入口，供 Verifier 作为机器证据来源。

### 已完成

- Windows: `.cursor/skills/verification/scripts/run-check.ps1`
  - 优先 `make check`
  - 无 `make` 时回退执行 Python 等价命令
  - 成功时输出 `All checks passed!`
- Linux/Mac: `.cursor/skills/verification/scripts/run-check.sh`
  - 同样优先 `make check`
  - 无 `make` 时回退执行 Python 等价命令
- 更新 `skills/verification/SKILL.md` 使用说明

### 待做

- 可选：脚本输出结构化 JSON（当前 ps1 支持 `-Json`，sh 未实现）
- 在 CI/不同环境下验证 `make` 不存在时的回退路径稳定性

