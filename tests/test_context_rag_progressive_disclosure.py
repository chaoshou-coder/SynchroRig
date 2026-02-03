import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".cursor" / "skills" / "context-rag" / "scripts" / "run-context-rag.ps1"
CONFIG = ROOT / ".cursor" / "skills" / "context-rag" / "config.json"


def _find_powershell():
    return shutil.which("pwsh") or shutil.which("powershell")


def _write_sample_files(repo_root: Path) -> None:
    progress = "\n".join(
        [
            "# PROGRESS（进度条）",
            "",
            "## 时间线（实时日志）",
            "",
            "| 时间(YYYY-MM-DD HH:mm:ss) | Task ID | Subagent | "
            "Phase | 做了什么 | 结果/证据 | 下一步 |",
            "|---|---|---|---|---|---|---|",
            "| 2026-02-03 21:23:34 | TASK-1 | orchestrator | implement | "
            "did a long step that should be summarized in index output | "
            "result detail one with extra context | next action |",
            "| 2026-02-03 21:24:34 | TASK-2 | implementers | implement | "
            "another long step that should be summarized as well | "
            "result detail two with extra context | next action |",
            "",
        ]
    )
    summary = "\n".join(
        [
            "# SUMMARY",
            "",
            "## 运行日志（按时间追加）",
            "",
            "| 时间(YYYY-MM-DD HH:mm:ss) | Task ID | Subagent | Phase | 事件 | 结果 | 下一步 |",
            "|---|---|---|---|---|---|---|",
            "| 2026-02-03 21:25:34 | TASK-1 | implementers | implement | "
            "candidate built tests before implementation | red then green | verifier |",
            "",
        ]
    )
    (repo_root / "PROGRESS.md").write_text(progress, encoding="utf-8")
    (repo_root / "SUMMARY.md").write_text(summary, encoding="utf-8")


def _write_config(path: Path) -> None:
    config = {
        "default": {
            "max_context_chars": 400,
            "max_context_tokens": 120,
            "budgets": {
                "index_tokens": 80,
                "timeline_tokens": 80,
                "detail_tokens": 80,
                "map_tokens": 80,
            },
        }
    }
    path.write_text(json.dumps(config), encoding="utf-8")


def _read_budgets(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    return config["default"]["budgets"]


def _run_context_rag(
    ps: str,
    repo_root: Path,
    mode: str,
    task_id: str | None = None,
    ids: list[str] | None = None,
    query: str | None = None,
):
    env = os.environ.copy()
    env["REPO_ROOT"] = str(repo_root)
    env["CONTEXT_RAG_CONFIG"] = str(repo_root / "config.json")

    cmd = [
        ps,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-Mode",
        mode,
    ]
    if task_id:
        cmd += ["-TaskId", task_id]
    if ids:
        cmd += ["-Ids", ",".join(ids)]
    if query:
        cmd += ["-Query", query]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    payload = json.loads(result.stdout)
    return payload, result.stdout


def _assert_budget(payload: dict, raw_output: str) -> None:
    budget_tokens = payload["metadata"]["budget_tokens"]
    tokens_approx = math.ceil(len(raw_output) / 4)
    assert tokens_approx <= budget_tokens


def test_context_rag_config_has_budgets():
    assert CONFIG.exists(), "Expected context-rag config.json to exist"
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    defaults = config.get("default", {})
    budgets = defaults.get("budgets", {})
    for key in ("index_tokens", "timeline_tokens", "detail_tokens", "map_tokens"):
        assert key in budgets, f"Missing required budget key: {key}"
    assert defaults.get("max_context_chars") or defaults.get("max_context_tokens")


def test_context_rag_payload_budget_matches_config(tmp_path):
    ps = _find_powershell()
    if not ps:
        pytest.skip("PowerShell not available")

    _write_sample_files(tmp_path)
    _write_config(tmp_path / "config.json")

    payload, _raw = _run_context_rag(ps, tmp_path, mode="index")
    assert payload["metadata"]["budget_tokens"] == 80


def test_context_rag_progressive_disclosure_shapes_and_budgets(tmp_path):
    ps = _find_powershell()
    if not ps:
        pytest.skip("PowerShell not available")

    _write_sample_files(tmp_path)
    _write_config(tmp_path / "config.json")
    budgets = _read_budgets(tmp_path / "config.json")

    index_payload, index_raw = _run_context_rag(ps, tmp_path, mode="index")
    assert index_payload["mode"] == "index"
    assert index_payload["items"]
    for item in index_payload["items"]:
        for key in ("id", "type", "task_id", "time", "summary"):
            assert key in item
        assert len(item["summary"]) <= 120
    assert index_payload["metadata"]["budget_tokens"] == budgets["index_tokens"]
    _assert_budget(index_payload, index_raw)
    assert "## PROGRESS" not in index_raw
    assert "## SUMMARY" not in index_raw

    timeline_payload, timeline_raw = _run_context_rag(
        ps, tmp_path, mode="timeline", task_id="TASK-1"
    )
    assert timeline_payload["mode"] == "timeline"
    assert timeline_payload["items"]
    assert {item["task_id"] for item in timeline_payload["items"]} == {"TASK-1"}
    assert timeline_payload["metadata"]["budget_tokens"] == budgets["timeline_tokens"]
    _assert_budget(timeline_payload, timeline_raw)

    first_id = index_payload["items"][0]["id"]
    detail_payload, detail_raw = _run_context_rag(ps, tmp_path, mode="detail", ids=[first_id])
    assert detail_payload["mode"] == "detail"
    assert [item["id"] for item in detail_payload["items"]] == [first_id]
    assert "detail" in detail_payload["items"][0]
    assert detail_payload["metadata"]["budget_tokens"] == budgets["detail_tokens"]
    _assert_budget(detail_payload, detail_raw)
