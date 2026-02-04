import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CURSOR_ROOT, ROOT

SCRIPT = CURSOR_ROOT / "scripts" / "candidate-preflight.ps1"


def find_powershell() -> str | None:
    if sys.platform.startswith("win"):
        return shutil.which("pwsh") or shutil.which("powershell")
    return shutil.which("pwsh")


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def run_git(repo_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return run_command(["git", "-C", str(repo_dir), *args])


def test_candidate_preflight_rejects_main_root_and_accepts_worktree(tmp_path: Path) -> None:
    powershell = find_powershell()
    if not powershell:
        pytest.skip("powershell not available")
    if not shutil.which("git"):
        pytest.skip("git not available")
    assert SCRIPT.exists(), "candidate-preflight.ps1 missing"

    repo_dir = tmp_path / "repo"
    worktree_dir = tmp_path / "worktree"
    repo_dir.mkdir(parents=True, exist_ok=True)

    result = run_git(repo_dir, ["init"])
    assert result.returncode == 0, result.stderr
    run_git(repo_dir, ["config", "user.email", "test@example.com"])
    run_git(repo_dir, ["config", "user.name", "Test User"])

    (repo_dir / "README.md").write_text("init", encoding="utf-8")
    result = run_git(repo_dir, ["add", "README.md"])
    assert result.returncode == 0, result.stderr
    result = run_git(repo_dir, ["commit", "-m", "init"])
    assert result.returncode == 0, result.stderr

    result = run_git(repo_dir, ["worktree", "add", str(worktree_dir)])
    assert result.returncode == 0, result.stderr

    try:
        result_main = run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-CandidateRepoRoot",
                str(repo_dir),
            ]
        )
        assert result_main.returncode != 0
        combined = (result_main.stderr + result_main.stdout).lower()
        assert "main repo root" in combined

        result_worktree = run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-CandidateRepoRoot",
                str(worktree_dir),
            ]
        )
        assert result_worktree.returncode == 0, result_worktree.stdout + result_worktree.stderr
    finally:
        run_git(repo_dir, ["worktree", "remove", "--force", str(worktree_dir)])
