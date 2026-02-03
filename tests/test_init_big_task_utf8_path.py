"""Regression tests for init-big-task.ps1: -TitlePath/-RequirementPath and UTF-8 output."""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".cursor" / "scripts" / "init-big-task.ps1"


def test_init_big_task_with_title_path_and_requirement_path_utf8(tmp_path):
    """Script -TitlePath/-RequirementPath reads UTF-8 files and writes UTF-8 SUMMARY/PROGRESS."""
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_content = "TitleFromFile-UTF8"
    req_content = "ReqFromFile-UTF8"
    title_file.write_text(title_content, encoding="utf-8")
    req_file.write_text(req_content, encoding="utf-8")

    # Run repo script with -RepoRoot so it writes to tmp_path (no script copy encoding issues)
    result = subprocess.run(
        [
            "powershell",
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


def test_init_big_task_rejects_implementers_role(tmp_path):
    """When CURSOR_AGENT=implementers, script exits with error (role guard)."""
    title_file = tmp_path / "title.txt"
    req_file = tmp_path / "req.txt"
    title_file.write_text("Title", encoding="utf-8")
    req_file.write_text("Req", encoding="utf-8")

    env = os.environ.copy()
    env["CURSOR_AGENT"] = "implementers"
    result = subprocess.run(
        [
            "powershell",
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
