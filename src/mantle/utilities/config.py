"""YAML configuration loading and validation."""

from pathlib import Path
from typing import Any
import yaml

from mantle.schemas.experiment import GlobalConfig


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping and raise clear errors for missing/invalid content."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"required configuration does not exist: {target}")
    with target.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration must be a mapping: {target}")
    return value


def load_global_config(root: str | Path) -> GlobalConfig:
    """Load and validate the Phase 1 global configuration."""
    return GlobalConfig.model_validate(load_yaml(Path(root) / "configs" / "global.yaml"))

