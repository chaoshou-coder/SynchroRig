from __future__ import annotations

from datetime import datetime
from typing import Mapping

from ..utils import parse_bool

CHECK_STATUSES = {"PASS", "FAIL", "ERROR"}
FINAL_STATUSES = {"PASS", "CHECK_FAIL", "INFRA_ERROR"}
FINAL_TO_CHECK = {
    "PASS": "PASS",
    "CHECK_FAIL": "FAIL",
    "INFRA_ERROR": "ERROR",
}


def _now_iso() -> str:
    return f"{datetime.utcnow().isoformat()}Z"


def _env_flag(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name)
    if value is None:
        return False
    return parse_bool(value, default=False)


def build_check(
    name: str,
    status: str,
    exit_code: int,
    command: str,
    *,
    stdout_excerpt: str = "",
    reason: str = "",
) -> dict:
    normalized_status = status.strip().upper()
    if normalized_status not in CHECK_STATUSES:
        raise ValueError(f"Unsupported check status: {status!r}")

    if normalized_status == "PASS":
        reason = reason or ""
        stdout_excerpt = stdout_excerpt or ""
    else:
        if not reason:
            reason = "Check error." if normalized_status == "ERROR" else "Check failed."
        stdout_excerpt = stdout_excerpt or ""

    return {
        "name": name,
        "status": normalized_status,
        "exit_code": int(exit_code),
        "command": command,
        "stdout_excerpt": stdout_excerpt,
        "reason": reason,
    }


def aggregate_status(checks: list[dict]) -> tuple[str, int]:
    if not checks:
        raise ValueError("checks must not be empty")

    statuses = {str(check.get("status", "")).upper() for check in checks}
    if "ERROR" in statuses:
        return "INFRA_ERROR", 2
    if "FAIL" in statuses:
        return "CHECK_FAIL", 1
    return "PASS", 0


def build_payload(
    mode: str,
    status: str,
    exit_code: int,
    checks: list[dict],
    *,
    banner: str = "",
    message: str = "",
    started_at: str | None = None,
    ended_at: str | None = None,
    duration_ms: int | None = None,
) -> dict:
    normalized_mode = (mode or "strict").strip().lower()
    normalized_status = status.strip().upper()
    if normalized_status not in FINAL_STATUSES:
        raise ValueError(f"Unsupported final status: {status!r}")

    if not checks:
        check_status = FINAL_TO_CHECK[normalized_status]
        fallback_reason = message if check_status != "PASS" else ""
        fallback_stdout = banner if check_status == "PASS" else ""
        checks = [
            build_check(
                "run-check",
                check_status,
                exit_code,
                normalized_mode,
                stdout_excerpt=fallback_stdout,
                reason=fallback_reason,
            )
        ]

    started_at = started_at or _now_iso()
    ended_at = ended_at or _now_iso()
    duration_ms = 0 if duration_ms is None else int(duration_ms)

    summary = {"all_checks_passed": normalized_status == "PASS", "banner": banner}
    return {
        "mode": normalized_mode,
        "status": normalized_status,
        "exit_code": int(exit_code),
        "checks": checks,
        "evidence": {"banner": banner, "message": message},
        "summary": summary,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
    }


def build_payload_from_checks(
    mode: str,
    checks: list[dict],
    *,
    banner: str | None = None,
    message: str = "",
    started_at: str | None = None,
    ended_at: str | None = None,
    duration_ms: int | None = None,
) -> dict:
    status, exit_code = aggregate_status(checks)
    if banner is None:
        banner = "All checks passed!" if status == "PASS" else ""
    return build_payload(
        mode,
        status,
        exit_code,
        checks,
        banner=banner,
        message=message,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=duration_ms,
    )


def build_contract_payload(
    env: Mapping[str, str],
    *,
    mode: str = "strict",
    started_at: str | None = None,
    ended_at: str | None = None,
    duration_ms: int | None = None,
) -> dict | None:
    if _env_flag(env, "RUN_CHECK_INFRA_ERROR"):
        check = build_check(
            "run-check",
            "ERROR",
            2,
            "infra error",
            reason="Infra error requested.",
        )
        return build_payload(
            mode,
            "INFRA_ERROR",
            2,
            [check],
            banner="",
            message="Infra error requested.",
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
        )

    if _env_flag(env, "RUN_CHECK_CONTRACT"):
        if _env_flag(env, "RUN_CHECK_CONTRACT_FAIL"):
            check = build_check(
                "run-check",
                "FAIL",
                1,
                "contract",
                reason="Contract mode requested failure.",
            )
            return build_payload(
                mode,
                "CHECK_FAIL",
                1,
                [check],
                banner="",
                message="Contract mode.",
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
            )

        check = build_check(
            "run-check",
            "PASS",
            0,
            "contract",
            stdout_excerpt="Contract mode.",
        )
        return build_payload(
            mode,
            "PASS",
            0,
            [check],
            banner="All checks passed!",
            message="Contract mode.",
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
        )

    return None
