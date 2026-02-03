import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_CHECK_PS1 = ROOT / ".cursor" / "skills" / "verification" / "scripts" / "run-check.ps1"
RUN_CHECK_SH = ROOT / ".cursor" / "skills" / "verification" / "scripts" / "run-check.sh"

REQUIRED_FIELDS = {
    "mode",
    "status",
    "exit_code",
    "checks",
    "evidence",
    "summary",
    "started_at",
    "ended_at",
    "duration_ms",
}


def find_powershell() -> str | None:
    if sys.platform.startswith("win"):
        return shutil.which("powershell") or shutil.which("pwsh")
    return shutil.which("pwsh")


def find_windows_powershell() -> str | None:
    if not sys.platform.startswith("win"):
        return None
    return shutil.which("powershell")


def find_bash() -> str | None:
    bash = shutil.which("bash") or shutil.which("sh")
    if not bash:
        return None
    if sys.platform.startswith("win"):
        bash_path = str(Path(bash).resolve()).lower()
        if bash_path.endswith("\\windows\\system32\\bash.exe"):
            return None
    return bash


def run_command(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, env=env)


def load_payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout.strip(), f"stdout empty; stderr={result.stderr!r}"
    return json.loads(result.stdout.strip())


def assert_contract_payload(payload: dict) -> None:
    assert REQUIRED_FIELDS.issubset(payload.keys())
    assert isinstance(payload["checks"], list)
    assert payload["checks"]
    assert isinstance(payload["evidence"], dict)
    assert isinstance(payload["summary"], dict)
    assert {"all_checks_passed", "banner"}.issubset(payload["summary"].keys())
    assert isinstance(payload["summary"]["all_checks_passed"], bool)
    assert isinstance(payload["summary"]["banner"], str)
    assert isinstance(payload["duration_ms"], int)
    assert payload["duration_ms"] >= 0
    assert isinstance(payload["started_at"], str)
    assert isinstance(payload["ended_at"], str)
    if payload["status"] == "PASS":
        assert payload["exit_code"] == 0
    elif payload["status"] == "CHECK_FAIL":
        assert payload["exit_code"] == 1
    elif payload["status"] == "INFRA_ERROR":
        assert payload["exit_code"] == 2
    for check in payload["checks"]:
        assert {"name", "status", "exit_code", "command"}.issubset(check.keys())
        assert check["status"] in {"PASS", "FAIL", "ERROR"}
        assert "stdout_excerpt" in check or "reason" in check
        if check["status"] == "PASS":
            assert check["exit_code"] == 0
            assert "stdout_excerpt" in check
            assert isinstance(check["stdout_excerpt"], str)
        else:
            assert check["exit_code"] != 0
            assert "reason" in check
            assert isinstance(check["reason"], str)
            assert check["reason"]
            if check["status"] == "ERROR":
                assert check["exit_code"] == 2


def build_stub_pythonpath(tmp_path: Path) -> str:
    stub_root = tmp_path / "stub_modules"
    for name in ("ruff", "pytest"):
        package = stub_root / name
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    return str(stub_root)


def env_with_stub_pythonpath(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    stub_root = build_stub_pythonpath(tmp_path)
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = stub_root if not pythonpath else stub_root + os.pathsep + pythonpath
    env.pop("RUN_CHECK_CONTRACT", None)
    env.pop("RUN_CHECK_CONTRACT_FAIL", None)
    env.pop("RUN_CHECK_INFRA_ERROR", None)
    return env


def build_stub_pythonpath_with_cwd_logs(tmp_path: Path) -> tuple[str, dict[str, Path]]:
    stub_root = tmp_path / "stub_modules_cwd"
    log_paths = {
        "ruff": tmp_path / "ruff_cwd.txt",
        "pytest": tmp_path / "pytest_cwd.txt",
    }
    for name, log_path in log_paths.items():
        package = stub_root / name
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            "import os\n"
            "from pathlib import Path\n"
            f"Path({str(log_path)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            "raise SystemExit(0)\n",
            encoding="utf-8",
        )
    return str(stub_root), log_paths


def env_with_stub_pythonpath_and_cwd_logs(
    tmp_path: Path,
) -> tuple[dict[str, str], dict[str, Path]]:
    env = os.environ.copy()
    stub_root, log_paths = build_stub_pythonpath_with_cwd_logs(tmp_path)
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = stub_root if not pythonpath else stub_root + os.pathsep + pythonpath
    env.pop("RUN_CHECK_CONTRACT", None)
    env.pop("RUN_CHECK_CONTRACT_FAIL", None)
    env.pop("RUN_CHECK_INFRA_ERROR", None)
    return env, log_paths


def assert_read_only_checks(payload: dict) -> None:
    commands = [str(check.get("command", "")).lower() for check in payload["checks"]]
    command_text = " ".join(commands)
    assert "ruff format" not in command_text
    assert "--fix" not in command_text
    assert any("ruff check" in command for command in commands)
    assert any("pytest" in command for command in commands)


@pytest.mark.parametrize(
    ("env_flag", "expected_status", "expected_exit"),
    [
        (None, "PASS", 0),
        ("RUN_CHECK_CONTRACT_FAIL", "CHECK_FAIL", 1),
        ("RUN_CHECK_INFRA_ERROR", "INFRA_ERROR", 2),
    ],
)
def test_run_check_ps1_strict_json_contract(env_flag, expected_status, expected_exit):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    env = os.environ.copy()
    env["RUN_CHECK_CONTRACT"] = "1"
    if env_flag:
        env[env_flag] = "1"

    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Mode",
            "strict",
            "-Format",
            "json",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == expected_status
    assert payload["exit_code"] == expected_exit
    assert result.returncode == expected_exit
    assert payload["summary"]["all_checks_passed"] is (expected_status == "PASS")
    if expected_status == "PASS":
        assert "All checks passed!" in payload["evidence"].get("banner", "")
        assert "All checks passed!" in payload["summary"].get("banner", "")
    else:
        assert "All checks passed!" not in payload["summary"].get("banner", "")


@pytest.mark.parametrize(
    ("env_flag", "expected_exit", "expects_banner"),
    [
        (None, 0, True),
        ("RUN_CHECK_CONTRACT_FAIL", 1, False),
    ],
)
def test_run_check_ps1_text_contract_windows_powershell(env_flag, expected_exit, expects_banner):
    powershell = find_windows_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("windows powershell not available or run-check.ps1 missing")

    env = os.environ.copy()
    env["RUN_CHECK_CONTRACT"] = "1"
    env.pop("RUN_CHECK_CONTRACT_FAIL", None)
    env.pop("RUN_CHECK_INFRA_ERROR", None)
    if env_flag:
        env[env_flag] = "1"

    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Mode",
            "strict",
            "-Format",
            "text",
        ],
        env,
    )

    assert result.returncode == expected_exit
    if expects_banner:
        assert "All checks passed!" in result.stdout
    else:
        assert "All checks passed!" not in result.stdout


@pytest.mark.parametrize(
    ("env_flag", "expected_exit", "expects_banner"),
    [
        (None, 0, True),
        ("RUN_CHECK_CONTRACT_FAIL", 1, False),
    ],
)
def test_run_check_ps1_text_contract_default_windows_powershell(
    env_flag, expected_exit, expects_banner
):
    powershell = find_windows_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("windows powershell not available or run-check.ps1 missing")

    env = os.environ.copy()
    env["RUN_CHECK_CONTRACT"] = "1"
    env.pop("RUN_CHECK_CONTRACT_FAIL", None)
    env.pop("RUN_CHECK_INFRA_ERROR", None)
    if env_flag:
        env[env_flag] = "1"

    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
        ],
        env,
    )

    assert result.returncode == expected_exit
    if expects_banner:
        assert "All checks passed!" in result.stdout
    else:
        assert "All checks passed!" not in result.stdout


def test_run_check_ps1_text_default_no_json_no_make(tmp_path):
    powershell = find_windows_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("windows powershell not available or run-check.ps1 missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-NoMake",
        ],
        env,
    )

    assert result.returncode == 0
    assert "All checks passed!" in result.stdout


def test_run_check_ps1_repo_root_overrides(tmp_path):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    repo_root = tmp_path / "repo_root"
    repo_root.mkdir(parents=True, exist_ok=True)
    env, log_paths = env_with_stub_pythonpath_and_cwd_logs(tmp_path)

    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-RepoRoot",
            str(repo_root),
            "-Format",
            "json",
            "-NoMake",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["status"] == "PASS"
    assert result.returncode == 0
    expected_root = repo_root.resolve()
    ruff_root = Path(log_paths["ruff"].read_text(encoding="utf-8").strip()).resolve()
    pytest_root = Path(log_paths["pytest"].read_text(encoding="utf-8").strip()).resolve()
    assert ruff_root == expected_root
    assert pytest_root == expected_root


@pytest.mark.parametrize(
    ("env_flag", "expected_status", "expected_exit"),
    [
        (None, "PASS", 0),
        ("RUN_CHECK_CONTRACT_FAIL", "CHECK_FAIL", 1),
        ("RUN_CHECK_INFRA_ERROR", "INFRA_ERROR", 2),
    ],
)
def test_run_check_sh_strict_json_contract(env_flag, expected_status, expected_exit):
    bash = find_bash()
    if not bash or not RUN_CHECK_SH.exists():
        pytest.skip("bash not available or run-check.sh missing")

    env = os.environ.copy()
    env["RUN_CHECK_CONTRACT"] = "1"
    if env_flag:
        env[env_flag] = "1"

    result = run_command(
        [
            bash,
            str(RUN_CHECK_SH),
            "--mode",
            "strict",
            "--format",
            "json",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == expected_status
    assert payload["exit_code"] == expected_exit
    assert result.returncode == expected_exit
    assert payload["summary"]["all_checks_passed"] is (expected_status == "PASS")
    if expected_status == "PASS":
        assert "All checks passed!" in payload["evidence"].get("banner", "")
        assert "All checks passed!" in payload["summary"].get("banner", "")
    else:
        assert "All checks passed!" not in payload["summary"].get("banner", "")


def test_run_check_ps1_default_mode_json_read_only(tmp_path):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Format",
            "json",
            "-NoMake",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_sh_default_mode_json_read_only(tmp_path):
    bash = find_bash()
    if not bash or not RUN_CHECK_SH.exists():
        pytest.skip("bash not available or run-check.sh missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            bash,
            str(RUN_CHECK_SH),
            "--format",
            "json",
            "--no-make",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_ps1_strict_read_only_no_make(tmp_path):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Mode",
            "strict",
            "-Format",
            "json",
            "-NoMake",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_sh_strict_read_only_no_make(tmp_path):
    bash = find_bash()
    if not bash or not RUN_CHECK_SH.exists():
        pytest.skip("bash not available or run-check.sh missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            bash,
            str(RUN_CHECK_SH),
            "--mode",
            "strict",
            "--format",
            "json",
            "--no-make",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_ps1_default_read_only_no_make(tmp_path):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Format",
            "json",
            "-NoMake",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_sh_default_read_only_no_make(tmp_path):
    bash = find_bash()
    if not bash or not RUN_CHECK_SH.exists():
        pytest.skip("bash not available or run-check.sh missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            bash,
            str(RUN_CHECK_SH),
            "--format",
            "json",
            "--no-make",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "strict"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_ps1_fast_read_only_no_make(tmp_path):
    powershell = find_powershell()
    if not powershell or not RUN_CHECK_PS1.exists():
        pytest.skip("powershell not available or run-check.ps1 missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_CHECK_PS1),
            "-Mode",
            "fast",
            "-Format",
            "json",
            "-NoMake",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "fast"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)


def test_run_check_sh_fast_read_only_no_make(tmp_path):
    bash = find_bash()
    if not bash or not RUN_CHECK_SH.exists():
        pytest.skip("bash not available or run-check.sh missing")

    env = env_with_stub_pythonpath(tmp_path)
    result = run_command(
        [
            bash,
            str(RUN_CHECK_SH),
            "--mode",
            "fast",
            "--format",
            "json",
            "--no-make",
        ],
        env,
    )

    payload = load_payload(result)
    assert_contract_payload(payload)
    assert payload["mode"] == "fast"
    assert payload["status"] == "PASS"
    assert payload["exit_code"] == 0
    assert result.returncode == 0
    assert payload["summary"]["all_checks_passed"] is True
    assert "All checks passed!" in payload["summary"].get("banner", "")
    assert_read_only_checks(payload)
