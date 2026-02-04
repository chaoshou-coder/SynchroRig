from pathlib import Path


def test_gitignore_ignores_runs_worktrees():
    repo_root = Path(__file__).resolve().parents[1]
    gitignore_path = repo_root / ".gitignore"
    assert gitignore_path.exists(), "Expected .gitignore to exist"

    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    allowed_rules = {
        "runs",
        "runs/",
        "runs/worktrees",
        "runs/worktrees/",
        "runs/worktrees/*",
        "runs/worktrees/**",
        "/runs/worktrees",
        "/runs/worktrees/",
        "/runs/worktrees/*",
        "/runs/worktrees/**",
    }
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line in allowed_rules:
            break
    else:
        raise AssertionError(
            "Expected .gitignore to ignore runs/worktrees/ (e.g. 'runs/worktrees/')"
        )


def test_gitignore_ignores_python_tool_caches():
    repo_root = Path(__file__).resolve().parents[1]
    gitignore_path = repo_root / ".gitignore"
    assert gitignore_path.exists(), "Expected .gitignore to exist"

    lines = gitignore_path.read_text(encoding="utf-8").splitlines()
    rules = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
    required_rules = {"__pycache__/", "*.pyc", ".pytest_cache/", ".ruff_cache/"}
    missing = sorted(required_rules - rules)
    if missing:
        raise AssertionError("Expected .gitignore to include: " + ", ".join(missing))
