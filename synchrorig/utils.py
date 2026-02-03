from __future__ import annotations


def parse_bool(value: object, *, default: bool | None = None) -> bool:
    """
    Parse a "truthy/falsey" value into a bool.

    Accepted inputs:
    - bool: returned as-is
    - int: 0 -> False, non-zero -> True
    - str (case-insensitive, trimmed):
      - true:  "1", "true", "t", "yes", "y", "on"
      - false: "0", "false", "f", "no", "n", "off", ""

    If parsing fails:
    - return `default` if provided
    - otherwise raise ValueError
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False

    if default is not None:
        return default

    raise ValueError(f"Cannot parse boolean from {value!r}")


def clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
