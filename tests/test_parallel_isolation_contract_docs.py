from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / ".cursor" / "rules"


def read_rules_text() -> str:
    parts = []
    for path in sorted(RULES_DIR.glob("*.mdc")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_parallel_isolation_contract_mentions_candidate_repo_root():
    text = read_rules_text()
    required_phrases = [
        "worktree.ps1 add",
        "runs/worktrees/<task_id>/<candidate_id>",
        "candidate_repo_root",
        "candidate-preflight.ps1 -CandidateRepoRoot",
        "run-check.ps1 -RepoRoot <candidate_repo_root>",
    ]
    for phrase in required_phrases:
        assert phrase in text
