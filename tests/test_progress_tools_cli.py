import sys
from pathlib import Path

from conftest import CURSOR_ROOT, ROOT

SCRIPTS_DIR = CURSOR_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import progress_tools  # noqa: E402


def test_event_allows_missing_task_id_value(monkeypatch):
    argv = [
        "progress_tools.py",
        "event",
        "--subagent",
        "orchestrator",
        "--phase",
        "plan",
        "--what",
        "start",
        "--task-id",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(progress_tools, "read_text", lambda path: "")
    monkeypatch.setattr(progress_tools, "write_text", lambda path, content: None)

    assert progress_tools.main() == 0


def test_event_default_paths_without_env_or_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(progress_tools, "repo_root_from_script", lambda: str(tmp_path))
    monkeypatch.delenv("SR_PROGRESS_PATH", raising=False)
    monkeypatch.delenv("SR_SUMMARY_PATH", raising=False)

    writes = []
    monkeypatch.setattr(progress_tools, "read_text", lambda path: "")
    monkeypatch.setattr(progress_tools, "write_text", lambda path, content: writes.append(path))

    argv = [
        "progress_tools.py",
        "event",
        "--subagent",
        "orchestrator",
        "--phase",
        "plan",
        "--what",
        "start",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert progress_tools.main() == 0
    assert writes == [str(tmp_path / "PROGRESS.md"), str(tmp_path / "SUMMARY.md")]


def test_event_env_paths_override_root(monkeypatch, tmp_path):
    monkeypatch.setattr(progress_tools, "repo_root_from_script", lambda: str(tmp_path))
    env_progress = tmp_path / "env" / "PROGRESS.md"
    env_summary = tmp_path / "env" / "SUMMARY.md"
    monkeypatch.setenv("SR_PROGRESS_PATH", str(env_progress))
    monkeypatch.setenv("SR_SUMMARY_PATH", str(env_summary))

    writes = []
    monkeypatch.setattr(progress_tools, "read_text", lambda path: "")
    monkeypatch.setattr(progress_tools, "write_text", lambda path, content: writes.append(path))

    argv = [
        "progress_tools.py",
        "event",
        "--subagent",
        "orchestrator",
        "--phase",
        "plan",
        "--what",
        "start",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert progress_tools.main() == 0
    assert writes == [str(env_progress), str(env_summary)]


def test_event_cli_overrides_env_and_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(progress_tools, "repo_root_from_script", lambda: str(tmp_path))

    root_progress = tmp_path / "PROGRESS.md"
    root_summary = tmp_path / "SUMMARY.md"
    root_progress.write_text("root progress", encoding="utf-8")
    root_summary.write_text("root summary", encoding="utf-8")

    env_progress = tmp_path / "env" / "PROGRESS.md"
    env_summary = tmp_path / "env" / "SUMMARY.md"
    monkeypatch.setenv("SR_PROGRESS_PATH", str(env_progress))
    monkeypatch.setenv("SR_SUMMARY_PATH", str(env_summary))

    cli_progress = tmp_path / "cli" / "nested" / "PROGRESS.md"
    cli_summary = tmp_path / "cli" / "nested" / "SUMMARY.md"

    argv = [
        "progress_tools.py",
        "event",
        "--subagent",
        "orchestrator",
        "--phase",
        "plan",
        "--what",
        "start",
        "--progress",
        str(cli_progress),
        "--summary",
        str(cli_summary),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert progress_tools.main() == 0
    assert cli_progress.exists()
    assert cli_summary.exists()
    assert not env_progress.exists()
    assert not env_summary.exists()
    assert root_progress.read_text(encoding="utf-8") == "root progress"
    assert root_summary.read_text(encoding="utf-8") == "root summary"


def test_task_cli_overrides_env_and_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(progress_tools, "repo_root_from_script", lambda: str(tmp_path))

    root_progress = tmp_path / "PROGRESS.md"
    root_summary = tmp_path / "SUMMARY.md"
    root_progress.write_text("root progress", encoding="utf-8")
    root_summary.write_text("root summary", encoding="utf-8")

    env_progress = tmp_path / "env" / "PROGRESS.md"
    env_summary = tmp_path / "env" / "SUMMARY.md"
    monkeypatch.setenv("SR_PROGRESS_PATH", str(env_progress))
    monkeypatch.setenv("SR_SUMMARY_PATH", str(env_summary))

    cli_progress = tmp_path / "cli" / "nested" / "PROGRESS.md"
    cli_summary = tmp_path / "cli" / "nested" / "SUMMARY.md"

    argv = [
        "progress_tools.py",
        "task",
        "--task-id",
        "T1",
        "--desc",
        "desc",
        "--risk",
        "low",
        "--status",
        "IN_PROGRESS",
        "--progress",
        str(cli_progress),
        "--summary",
        str(cli_summary),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert progress_tools.main() == 0
    assert cli_progress.exists()
    assert cli_summary.exists()
    assert not env_progress.exists()
    assert not env_summary.exists()
    assert root_progress.read_text(encoding="utf-8") == "root progress"
    assert root_summary.read_text(encoding="utf-8") == "root summary"


def test_render_cli_overrides_env_and_creates_parent_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(progress_tools, "repo_root_from_script", lambda: str(tmp_path))

    root_progress = tmp_path / "PROGRESS.md"
    root_summary = tmp_path / "SUMMARY.md"
    root_progress.write_text("root progress", encoding="utf-8")
    root_summary.write_text("root summary", encoding="utf-8")

    env_progress = tmp_path / "env" / "PROGRESS.md"
    env_summary = tmp_path / "env" / "SUMMARY.md"
    monkeypatch.setenv("SR_PROGRESS_PATH", str(env_progress))
    monkeypatch.setenv("SR_SUMMARY_PATH", str(env_summary))

    cli_progress = tmp_path / "cli" / "nested" / "PROGRESS.md"
    cli_summary = tmp_path / "cli" / "nested" / "SUMMARY.md"

    argv = [
        "progress_tools.py",
        "render",
        "--progress",
        str(cli_progress),
        "--summary",
        str(cli_summary),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert progress_tools.main() == 0
    assert cli_progress.exists()
    assert cli_summary.exists()
    assert not env_progress.exists()
    assert not env_summary.exists()
    assert root_progress.read_text(encoding="utf-8") == "root progress"
    assert root_summary.read_text(encoding="utf-8") == "root summary"
