from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULE_PATH = ROOT / ".cursor" / "rules" / "orchestration.mdc"


def test_orchestration_rule_removes_context_rag_precondition():
    text = RULE_PATH.read_text(encoding="utf-8")
    assert "context-rag" not in text
    assert "Subagent 上下文供给（RAG" not in text
    assert "调用 context-rag skill" not in text
