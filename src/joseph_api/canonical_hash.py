"""Canonical JSON encoding and hashing for content-addressed contracts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any


def canonical_json_bytes(value: object) -> bytes:
    """Return the stable UTF-8 JSON encoding used by content-addressed contracts."""
    payload = _canonical_value(value)
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Return a tagged SHA-256 digest over :func:`canonical_json_bytes`."""
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_value(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonical_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical datetimes must be timezone-aware")
        normalized = value.astimezone(UTC).isoformat(timespec="microseconds")
        return normalized.replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical mappings require string keys")
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical floats must be finite")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


canonical_json_bytes.__module__ = "joseph_core.dal.observation.identity"
canonical_sha256.__module__ = "joseph_core.dal.observation.identity"
