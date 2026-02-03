import pytest

from synchrorig.utils import clamp, parse_bool


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("TRUE", True),
        (" yes ", True),
        ("on", True),
        ("false", False),
        ("OFF", False),
        ("", False),
        ("  ", False),
    ],
)
def test_parse_bool_valid(value, expected):
    assert parse_bool(value) is expected


def test_parse_bool_invalid_raises():
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_parse_bool_invalid_default():
    assert parse_bool("maybe", default=True) is True


@pytest.mark.parametrize(
    ("value", "lo", "hi", "expected"),
    [
        (-5, 0, 10, 0),
        (15, 0, 10, 10),
        (0, 0, 10, 0),
        (5, 0, 10, 5),
        (10, 0, 10, 10),
    ],
)
def test_clamp_value(value, lo, hi, expected):
    assert clamp(value, lo, hi) == expected
