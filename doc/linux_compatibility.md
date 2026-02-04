# Linux 兼容性说明

## 总体结论

- **CI（GitHub Actions）**：在 `ubuntu-latest` 上运行 `make check`（format / lint / test）**可过**，前提是测试通过「模板目录」解析（见下方修复）。
- **本地 Linux**：`make check`、`run-check.sh`、`init-big-task.sh` 可用；Orchestrator 规则中部分脚本仅提供 PowerShell 版，需 `pwsh` 或后续补充 `.sh` 才能完整工作流。

---

## 已兼容部分

| 组件 | 说明 |
|------|------|
| **Makefile** | 使用 `python -m ruff` / `pytest`，与平台无关 |
| **CI (.github/workflows/check.yml)** | `runs-on: ubuntu-latest`，仅执行 `make check` |
| **verification skill** | 提供 `run-check.ps1` 与 `run-check.sh`；Linux 使用 `run-check.sh` |
| **init-big-task** | 提供 `init-big-task.ps1` 与 `init-big-task.sh`，参数一致 |
| **Python 代码 (synchrorig/, progress_tools.py)** | 使用 `open(..., encoding="utf-8")`、无硬编码反斜杠 |
| **test_run_check_contract** | 对 Windows 的 `bash.exe` 判断仅在本机为 Windows 时执行，Linux 正常用 bash |

---

## 需注意 / 已修复

### 1. 测试依赖 `.cursor` 路径

- **问题**：多处测试写死 `ROOT / ".cursor" / ...`，CI 克隆后只有 `template-cursor`，无 `.cursor`，会导致 `FileNotFoundError`。
- **处理**：在 `conftest.py` 中定义 `CURSOR_ROOT`，优先使用 `.cursor`（本地），不存在时用 `template-cursor`（CI）。相关测试改为使用 `CURSOR_ROOT`。

### 2. init-big-task 模板一致性与“当前时间/总进度”

- **问题**：`init-big-task.sh` 的 PROGRESS 模板仍含「当前时间」「总进度」两行，与规则/测试期望（已移除）不一致；`init-big-task.ps1` 若也含这两行，会与 `test_progress_header` 冲突。
- **处理**：从 `init-big-task.sh` 与 `init-big-task.ps1` 的 PROGRESS 模板中移除这两行，与 `test_progress_header` 及文档一致。

### 3. 仅提供 PowerShell 的脚本（Linux 需 pwsh）

以下脚本目前只有 `.ps1`，无对应 `.sh`；在纯 Linux 环境下若由 Orchestrator 规则直接调用，需安装 **PowerShell Core**（`pwsh`）：

- `log-event.ps1`
- `upsert-task.ps1`
- `tail-progress.ps1` / `tail-summary.ps1`
- `finalize-big-task.ps1`
- `candidate-preflight.ps1`
- `worktree.ps1`

**建议**：Linux 用户安装 `pwsh`，或后续为上述脚本提供等价的 `.sh` 实现。

### 4. context-rag / consultation skill

- `template-cursor/skills/` 下仅包含 **compression** 与 **verification**。
- **context-rag**、**consultation** 若仅存在于本地 `.cursor`，则依赖它们的测试在 CI（无 `.cursor`）中会因路径不存在而失败；已通过“路径存在再测”或使用 `CURSOR_ROOT` 等方式避免误报。

---

## 推荐用法（Linux）

```bash
# 1) 克隆后复制模板
cp -r template-cursor .cursor

# 2) 验证
make check

# 3) 运行验收（与 Windows 等效）
.cursor/skills/verification/scripts/run-check.sh

# 4) 初始化大任务（bash）
.cursor/scripts/init-big-task.sh "标题" "需求摘要"
```

若需使用 `log-event`、`upsert-task` 等，请安装 PowerShell Core 后调用对应 `.ps1`，或等待仓库提供 `.sh` 版本。
