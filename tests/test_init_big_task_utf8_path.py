"""Regression tests for init-big-task.ps1: -TitlePath/-RequirementPath and UTF-8 output."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CURSOR_ROOT

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = CURSOR_ROOT / "scripts" / "init-big-task.ps1"


def find_windows_powershell_exe() -> str | None:
    if not sys.platform.startswith("win"):
        return None
    return shutil.which("powershell.exe")


def test_init_big_task_with_title_path_and_requirement_path_utf8(tmp_path):
    """Script -TitlePath/-RequirementPath reads UTF-8 files and writes UTF-8 SUMMARY/PROGRESS."""
    powershell = find_windows_powershell_exe()
    if not powershell:
        pytest.skip("powershell.exe not available")
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_content = "TitleFromFile-UTF8"
    req_content = "ReqFromFile-UTF8"
    title_file.write_text(title_content, encoding="utf-8")
    req_file.write_text(req_content, encoding="utf-8")

    # Run repo script with -RepoRoot so it writes to tmp_path (no script copy encoding issues)
    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-TitlePath",
            str(title_file),
            "-RequirementPath",
            str(req_file),
            "-RepoRoot",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")

    summary_path = tmp_path / "SUMMARY.md"
    progress_path = tmp_path / "PROGRESS.md"
    assert summary_path.exists()
    assert progress_path.exists()

    summary_bytes = summary_path.read_bytes()
    progress_bytes = progress_path.read_bytes()
    summary_text = summary_bytes.decode("utf-8")
    progress_text = progress_bytes.decode("utf-8")

    assert title_content in summary_text
    assert req_content in summary_text
    assert title_content in progress_text
    assert req_content in progress_text
    summary_bytes.decode("utf-8", errors="strict")
    progress_bytes.decode("utf-8", errors="strict")


def test_init_big_task_outputs_utf8_without_bom(tmp_path):
    """Generated files should be UTF-8 without BOM."""
    powershell = find_windows_powershell_exe()
    if not powershell:
        pytest.skip("powershell.exe not available")
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_file.write_text("TitleUTF8", encoding="utf-8")
    req_file.write_text("RequirementUTF8", encoding="utf-8")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-TitlePath",
            str(title_file),
            "-RequirementPath",
            str(req_file),
            "-RepoRoot",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")

    summary_bytes = (tmp_path / "SUMMARY.md").read_bytes()
    progress_bytes = (tmp_path / "PROGRESS.md").read_bytes()
    assert not summary_bytes.startswith(b"\xef\xbb\xbf")
    assert not progress_bytes.startswith(b"\xef\xbb\xbf")
    summary_bytes.decode("utf-8", errors="strict")
    progress_bytes.decode("utf-8", errors="strict")


def test_init_big_task_utf8_template_chinese_lines(tmp_path):
    """Windows PowerShell 5 emits correct Chinese template lines."""
    powershell = find_windows_powershell_exe()
    if not powershell or not SCRIPT_PATH.exists():
        pytest.skip("powershell.exe not available or script missing")
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_file.write_text("TitleUTF8", encoding="utf-8")
    req_file.write_text("RequirementUTF8", encoding="utf-8")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-TitlePath",
            str(title_file),
            "-RequirementPath",
            str(req_file),
            "-RepoRoot",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (result.stdout or "") + (result.stderr or "")

    summary_path = tmp_path / "SUMMARY.md"
    progress_path = tmp_path / "PROGRESS.md"
    summary_bytes = summary_path.read_bytes()
    progress_bytes = progress_path.read_bytes()
    summary_text = summary_bytes.decode("utf-8", errors="strict")
    progress_text = progress_bytes.decode("utf-8", errors="strict")

    assert "> 大任务运行摘要（本次运行 append-only）" in summary_text
    assert "## 运行日志（按时间追加）" in summary_text
    assert "| 时间(YYYY-MM-DD HH:mm:ss) | Subagent | Phase | 事件 | 结果 | 下一步 |" in summary_text
    assert "# PROGRESS（进度条）" in progress_text
    assert "## 子任务清单（PR 粒度）" in progress_text
    assert "## 时间线（实时日志）" in progress_text
    # Accept either: with 结果/证据 (template-cursor) or with Task ID column (legacy .cursor)
    has_result_col = "结果/证据" in progress_text and "做了什么" in progress_text
    has_task_id_timeline = "Task ID" in progress_text and "Subagent" in progress_text
    assert has_result_col or has_task_id_timeline, "Timeline table must have 结果/证据 or Task ID column"


def test_init_big_task_rejects_implementers_role(tmp_path):
    """When CURSOR_AGENT=implementers, script exits with error (role guard)."""
    powershell = find_windows_powershell_exe()
    if not powershell:
        pytest.skip("powershell.exe not available")
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_file.write_text("Title", encoding="utf-8")
    req_file.write_text("Req", encoding="utf-8")

    env = os.environ.copy()
    env["CURSOR_AGENT"] = "implementers"
    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT_PATH),
            "-TitlePath",
            str(title_file),
            "-RequirementPath",
            str(req_file),
            "-RepoRoot",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert result.returncode != 0
