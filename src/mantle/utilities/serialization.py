"""Canonical JSON serialization and SHA-256 hashing."""

from pathlib import Path
from typing import Any
import hashlib
import json


def canonical_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data with deterministic key and whitespace rules."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_value(value: Any) -> str:
    """Hash a canonical JSON-compatible value."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: str | Path, value: Any) -> str:
    """Write canonical UTF-8 JSON and return its SHA-256 hash."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    target.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def read_json(path: str | Path) -> Any:
    """Read a UTF-8 JSON artifact."""
    return json.loads(Path(path).read_text(encoding="utf-8"))

