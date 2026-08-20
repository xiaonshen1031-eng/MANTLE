"""Conversion provenance helpers."""

from pathlib import Path
import hashlib


def file_sha256(path: str | Path) -> str:
    """Return a file SHA-256 digest."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

