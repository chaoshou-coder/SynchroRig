import sys
import textwrap
from pathlib import Path

from conftest import CURSOR_ROOT, ROOT

SCRIPTS_DIR = CURSOR_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import progress_tools  # noqa: E402


def test_generate_report_includes_required_sections():
    summary_md = (
        textwrap.dedent(
            """
            # SUMMARY

            > 大任务运行摘要（本次运行 append-only）

            ## 大任务

            - **标题**：Demo Report Task
            - **开始时间**：2026-02-01 10:00:00

            ### 需求原文/摘要

            生成最终报告

            ## 变更文件列表
            - src/app.py
            - .cursor/scripts/progress_tools.py

            ## 变更概览
            - 增加报告生成
            - 添加 finalize 脚本

            ## 运行日志（按时间追加）

            | 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |
            |---|---|---|---|---|---|
            | 2026-02-01 10:05:00 | planner | plan | 拆分子任务 | T1, T2 | 开始实现 |
            | 2026-02-01 10:35:00 | verifier | verify | Verified T1_FOO | PASS | Run T2 |
            """
        ).strip()
        + "\n"
    )
    progress_md = (
        textwrap.dedent(
            """
            # PROGRESS（进度条）

            ## 大任务

            - **标题**：Demo Report Task
            - **开始时间**：2026-02-01 10:00:00

            ### 需求原文/摘要

            生成最终报告

            ## 子任务清单（PR 粒度）

            | 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |
            |---|---|---|---|---|---|---|
            | 1 | T1_FOO | Add foo | low | PASS | 2026-02-01 10:15:00 | run-check ok |
            | 2 | T2_BAR | Add bar | medium | PASS | 2026-02-01 10:40:00 | run-check ok |

            ## 时间线（实时日志）

            | 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |
            |---|---|---|---|---|---|
            | 2026-02-01 10:10:00 | impl | implement | T1_FOO start | tests | pytest |
            | 2026-02-01 10:15:00 | verify | verify | T1_FOO ok | PASS | next |
            | 2026-02-01 10:25:00 | impl | implement | T2_BAR start | tests | pytest |
            | 2026-02-01 10:40:00 | verify | verify | T2_BAR ok | PASS | done |
            """
        ).strip()
        + "\n"
    )

    report = progress_tools.generate_report(summary_md, progress_md)

    assert "# REPORT" in report
    assert "## 大任务概览" in report
    assert "开始时间" in report
    assert "结束时间" in report
    assert "总耗时" in report
    assert "## 子任务列表" in report
    assert "T1_FOO" in report
    assert "T2_BAR" in report
    assert "## 大任务时间线" in report
    assert "## 子任务时间线与耗时" in report
    assert "### T1_FOO" in report
    assert "00:05:00" in report
    assert "### T2_BAR" in report
    assert "00:15:00" in report
    assert "2026-02-01 10:40:00" in report
    assert "## 变更概览" in report
    assert "src/app.py" in report
    assert "增加报告生成" in report


def test_generate_report_supports_old_timeline_format():
    summary_md = "# SUMMARY\n\n"
    progress_md = (
        textwrap.dedent(
            """
            # PROGRESS（进度条）

            ## 时间线（实时日志）

            | 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 做了什么 | 结果/证据 | 下一步 |
            |---|---|---|---|---|---|
            | 2026-02-02 10:00:00 | orchestrator | plan | legacy event | ok | next |
            """
        ).strip()
        + "\n"
    )

    report = progress_tools.generate_report(summary_md, progress_md)

    assert "## 大任务时间线" in report
    assert "legacy event" in report
    assert "## 子任务时间线与耗时" in report


def test_generate_report_uses_task_id_column_for_duration():
    summary_md = "# SUMMARY\n\n"
    progress_md = "\n".join(
        [
            "# PROGRESS（进度条）",
            "",
            "## 子任务清单（PR 粒度）",
            "",
            "| 序号 | Task ID | 描述 | 风险 | 状态 | 最新更新时间 | 验收证据 |",
            "|---|---|---|---|---|---|---|",
            "| 1 | T2 | Add report | low | PASS | 2026-02-02 10:12:30 | ok |",
            "",
            "## 时间线（实时日志）",
            "",
            (
                "| 时间(YYYY-MM-DD HH:mm:ss) | Task ID | Subagent | Phase | 做了什么 | "
                "结果/证据 | 下一步 |"
            ),
            "|---|---|---|---|---|---|---|",
            "| 2026-02-02 10:00:00 | T2 | implementers | implement | 开始实现 | | |",
            "| 2026-02-02 10:12:30 | T2 | implementers | implement | 完成实现 | | |",
            "",
        ]
    )

    report = progress_tools.generate_report(summary_md, progress_md)

    assert "### T2" in report
    assert "- **开始时间**：2026-02-02 10:00:00" in report
    assert "- **结束时间**：2026-02-02 10:12:30" in report
    assert "- **耗时**：00:12:30" in report
