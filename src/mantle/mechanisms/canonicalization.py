"""Tolerance-free canonicalization for exact discrete mechanisms."""

from __future__ import annotations

from typing import Any


def canonicalize(value: Any) -> Any:
    """Convert nested dictionaries/lists/dataclasses to immutable sorted tuples."""

    if hasattr(value, "__dataclass_fields__"):
        return canonicalize(tuple(getattr(value, field) for field in value.__dataclass_fields__))
    if isinstance(value, dict):
        return tuple((key, canonicalize(value[key])) for key in sorted(value))
    if isinstance(value, (list, tuple)):
        return tuple(canonicalize(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((canonicalize(item) for item in value), key=repr))
    return value


def equivalent(left: Any, right: Any) -> bool:
    """Exact equivalence; approximate/tolerance-based merging is forbidden."""

    return canonicalize(left) == canonicalize(right)
