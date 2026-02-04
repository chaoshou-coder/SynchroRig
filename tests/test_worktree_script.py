import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CURSOR_ROOT, ROOT

SCRIPT = CURSOR_ROOT / "scripts" / "worktree.ps1"


def find_powershell() -> str | None:
    if sys.platform.startswith("win"):
        return shutil.which("pwsh") or shutil.which("powershell")
    return shutil.which("pwsh")


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd)


def run_git(repo_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return run_command(["git", "-C", str(repo_dir), *args])


def init_repo(repo_dir: Path) -> None:
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


def last_non_empty_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assert lines, "expected output"
    return lines[-1]


def normalize_path(text: str) -> str:
    return text.replace("\\", "/")


def test_worktree_script_help_shows_subcommands() -> None:
    powershell = find_powershell()
    if not powershell:
        pytest.skip("powershell not available")
    assert SCRIPT.exists(), "worktree.ps1 missing"

    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Help",
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    combined = (result.stdout + result.stderr).lower()
    for token in ("add", "list", "remove"):
        assert token in combined


def test_worktree_script_add_list_remove(tmp_path: Path) -> None:
    powershell = find_powershell()
    if not powershell:
        pytest.skip("powershell not available")
    if not shutil.which("git"):
        pytest.skip("git not available")
    assert SCRIPT.exists(), "worktree.ps1 missing"

    repo_dir = tmp_path / "repo"
    init_repo(repo_dir)

    def run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
        return run_command(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                *args,
            ]
        )

    add_result = run_script(
        ["add", "-TaskId", "T001", "-CandidateId", "CANDIDATE_1", "-RepoRoot", str(repo_dir)]
    )
    assert add_result.returncode == 0, add_result.stdout + add_result.stderr
    worktree_path = Path(last_non_empty_line(add_result.stdout))
    assert worktree_path.is_absolute()
    assert worktree_path.exists()
    list_result = run_script(["list", "-RepoRoot", str(repo_dir)])
    assert list_result.returncode == 0, list_result.stdout + list_result.stderr
    assert worktree_path.as_posix() in normalize_path(list_result.stdout)

    add_result_2 = run_script(
        ["add", "-TaskId", "T001", "-CandidateId", "CANDIDATE_1", "-RepoRoot", str(repo_dir)]
    )
    assert add_result_2.returncode == 0, add_result_2.stdout + add_result_2.stderr
    worktree_path_2 = Path(last_non_empty_line(add_result_2.stdout))
    assert worktree_path_2.is_absolute()
    assert worktree_path_2 != worktree_path
    assert worktree_path_2.name == "CANDIDATE_1-r1"
    assert worktree_path_2.exists()
    list_result_2 = run_script(["list", "-RepoRoot", str(repo_dir)])
    assert list_result_2.returncode == 0, list_result_2.stdout + list_result_2.stderr
    normalized_list = normalize_path(list_result_2.stdout)
    assert worktree_path.as_posix() in normalized_list
    assert worktree_path_2.as_posix() in normalized_list

    remove_result_2 = run_script(
        [
            "remove",
            "-TaskId",
            "T001",
            "-CandidateId",
            worktree_path_2.name,
            "-RepoRoot",
            str(repo_dir),
            "-DeleteDir",
        ]
    )
    assert remove_result_2.returncode == 0, remove_result_2.stdout + remove_result_2.stderr
    remove_result = run_script(
        [
            "remove",
            "-TaskId",
            "T001",
            "-CandidateId",
            "CANDIDATE_1",
            "-RepoRoot",
            str(repo_dir),
            "-DeleteDir",
        ]
    )
    assert remove_result.returncode == 0, remove_result.stdout + remove_result.stderr
    list_after = run_git(repo_dir, ["worktree", "list"])
    assert list_after.returncode == 0, list_after.stderr
    normalized_after = normalize_path(list_after.stdout)
    assert worktree_path.as_posix() not in normalized_after
    assert worktree_path_2.as_posix() not in normalized_after
