from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

import pytest

from joseph_api.canonical_hash import canonical_json_bytes, canonical_sha256


class Color(Enum):
    RED = "red"


@dataclass(frozen=True)
class Point:
    x: int
    y: int


def test_canonical_bytes_are_sorted_and_compact():
    payload = {"b": 1, "a": [1, 2], "t": (1, 2)}
    assert canonical_json_bytes(payload) == b'{"a":[1,2],"b":1,"t":[1,2]}'


def test_dates_enums_dataclasses_and_utc_datetimes():
    out = canonical_json_bytes(
        {
            "d": __import__("datetime").date(2024, 1, 2),
            "e": Color.RED,
            "p": Point(1, 2),
            "t": datetime(2024, 1, 2, 3, 4, 5, 6, tzinfo=UTC),
            "z": datetime(
                2024,
                1,
                2,
                3,
                4,
                5,
                6,
                tzinfo=__import__("datetime").timezone(__import__("datetime").timedelta(hours=8)),
            ),
        }
    )
    assert out == (
        b'{"d":"2024-01-02","e":"red","p":{"x":1,"y":2},'
        b'"t":"2024-01-02T03:04:05.000006Z","z":"2024-01-01T19:04:05.000006Z"}'
    )


def test_non_finite_floats_and_naive_datetimes_are_rejected():
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical_json_bytes({"x": datetime(2024, 1, 2)})


def test_non_string_keys_are_rejected():
    with pytest.raises(TypeError):
        canonical_json_bytes({1: "a"})


def test_sha256_is_tagged_and_stable():
    assert canonical_sha256({"a": 1}).startswith("sha256:")
    assert canonical_sha256({"a": 1}) == canonical_sha256({"a": 1})
