"""Regenerate the three deterministic MANTLE-ready coupled-system packages."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mantle.systems.coupled_system import build_all_coupled_systems


if __name__ == "__main__":
    print(json.dumps(build_all_coupled_systems(ROOT), indent=2, sort_keys=True))
