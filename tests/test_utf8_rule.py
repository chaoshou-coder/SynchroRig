from pathlib import Path

import pytest


def test_utf8_rule_present_and_keywords():
    from conftest import CURSOR_ROOT

    rule_path = CURSOR_ROOT / "rules" / "utf8-encoding.mdc"
    assert rule_path.exists(), f"Expected {CURSOR_ROOT}/rules/utf8-encoding.mdc to exist"

    data = rule_path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        pytest.fail(f"utf8-encoding.mdc is not valid UTF-8: {exc}")

    assert "UTF-8" in text
    assert "-Encoding UTF8" in text
