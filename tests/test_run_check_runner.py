import pytest

from synchrorig.run_check.runner import build_contract_payload, build_payload

FIXED_START = "2026-02-02T00:00:00Z"
FIXED_END = "2026-02-02T00:00:01Z"


@pytest.mark.parametrize(
    ("env", "expected_status", "expected_exit", "check_status", "expects_banner"),
    [
        ({"RUN_CHECK_CONTRACT": "1"}, "PASS", 0, "PASS", True),
        (
            {"RUN_CHECK_CONTRACT": "1", "RUN_CHECK_CONTRACT_FAIL": "1"},
            "CHECK_FAIL",
            1,
            "FAIL",
            False,
        ),
        ({"RUN_CHECK_INFRA_ERROR": "1"}, "INFRA_ERROR", 2, "ERROR", False),
    ],
)
def test_build_contract_payload_variants(
    env, expected_status, expected_exit, check_status, expects_banner
):
    payload = build_contract_payload(
        env,
        mode="strict",
        started_at=FIXED_START,
        ended_at=FIXED_END,
        duration_ms=1000,
    )

    assert payload is not None
    assert payload["mode"] == "strict"
    assert payload["status"] == expected_status
    assert payload["exit_code"] == expected_exit
    assert payload["started_at"] == FIXED_START
    assert payload["ended_at"] == FIXED_END
    assert payload["duration_ms"] == 1000
    assert payload["checks"]

    check = payload["checks"][0]
    assert check["status"] == check_status

    if check_status == "PASS":
        assert check["stdout_excerpt"]
        assert payload["summary"]["all_checks_passed"] is True
        assert "All checks passed!" in payload["summary"]["banner"]
        assert expects_banner
    else:
        assert check["reason"]
        assert payload["summary"]["all_checks_passed"] is False
        assert "All checks passed!" not in payload["summary"]["banner"]
        assert not expects_banner


def test_build_contract_payload_returns_none_without_flags():
    assert build_contract_payload({}, mode="strict") is None


def test_build_payload_defaults_to_strict_mode():
    payload = build_payload(
        mode="",
        status="PASS",
        exit_code=0,
        checks=[],
        banner="All checks passed!",
        message="",
        started_at=FIXED_START,
        ended_at=FIXED_END,
        duration_ms=1000,
    )

    assert payload["mode"] == "strict"
