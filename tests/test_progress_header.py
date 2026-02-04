import sys
from pathlib import Path

from conftest import CURSOR_ROOT, ROOT

SCRIPTS_DIR = CURSOR_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import progress_tools  # noqa: E402


def read_repo_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_init_big_task_ps1_omits_time_and_progress_lines():
    content = (CURSOR_ROOT / "scripts" / "init-big-task.ps1").read_text(encoding="utf-8")
    assert "- **当前时间**" not in content
    assert "- **总进度**" not in content


def test_init_big_task_sh_omits_time_and_progress_lines():
    content = (CURSOR_ROOT / "scripts" / "init-big-task.sh").read_text(encoding="utf-8")
    assert "- **当前时间**" not in content
    assert "- **总进度**" not in content


def test_recompute_overview_no_longer_updates_header_lines():
    progress_md = (
        "# PROGRESS（进度条）\n\n"
        "## 大任务\n\n"
        "- **标题**：X\n"
        "- **开始时间**：2000-01-01 00:00:00\n"
        "- **当前时间**：2000-01-01 00:00:00\n"
        "- **总进度**：0/0（0%） [--------------------]\n\n"
        "## 子任务清单（PR 粒度）\n\n"
        "| 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |\n"
        "|---|---|---|---|---|---|---|\n"
        "## 时间线（实时日志）\n\n"
        "| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |\n"
        "|---|---|---|---|---|---|\n"
    )
    assert progress_tools.recompute_overview(progress_md) == progress_md
