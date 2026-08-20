"""Integrity checks for bundled original and MANTLE-ready system data."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_all_system_packages_exist() -> None:
    for system_id in ("ieee14", "ieee39", "rts_gmlc"):
        path = ROOT / "data" / "modified" / system_id / "coupled_system.json"
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["system_id"] == system_id
        assert data["power"]["buses"]
        assert data["power"]["branches"]
        assert data["communication"]["nodes"]
        assert data["missions"]


def test_original_sources_exist() -> None:
    assert (ROOT / "data/original/ieee14/case14.json").is_file()
    assert (ROOT / "data/original/ieee39/case39.json").is_file()
    for name in ("bus.csv", "branch.csv", "gen.csv", "RTS_GMLC.m", "pandapower_net.json"):
        assert (ROOT / "data" / "original" / "rts_gmlc" / name).is_file()

