"""Build complete serializable power-communication-mission-resource systems."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib

from mantle.restoration.resources import build_resources
from mantle.schemas.power import Generator, PowerBranch, PowerBus, Storage
from mantle.systems.communication_system import build_communication_variants
from mantle.systems.mission_system import build_missions
from mantle.systems.power_system import extract_power_components, load_network, select_rts_windows
from mantle.utilities.config import load_yaml
from mantle.utilities.reproducibility import SeedManager
from mantle.utilities.serialization import write_json


def _source_hashes(root: Path, system_id: str) -> dict[str, str]:
    """Hash all immutable source files used by a system."""
    original = root / "data" / "original" / system_id
    return {
        str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(original.iterdir()) if path.is_file()
    }


def build_coupled_system(root: str | Path, system_id: str) -> dict[str, Any]:
    """Build and write one deterministic coupled-system package."""
    root_path = Path(root)
    global_config = load_yaml(root_path / "configs" / "global.yaml")
    system_config = load_yaml(root_path / "configs" / "systems" / f"{system_id}.yaml")
    comm_config = load_yaml(root_path / "configs" / "communication" / f"{system_id}_comm.yaml")
    mission_config = load_yaml(root_path / "configs" / "missions" / f"{system_id}_missions.yaml")
    resource_config = load_yaml(root_path / "configs" / "restoration" / f"{system_id}_resources.yaml")
    seed_manager = SeedManager(int(global_config["random_seed"]))
    net = load_network(root_path, system_id)
    power = extract_power_components(root_path, system_id, net)
    mission_buses = {str(bus) for item in mission_config["missions"] for bus in item["mapped_power_buses"]}
    for bus in power["buses"]:
        bus["critical_load_flag"] = bus["bus_id"] in mission_buses
        PowerBus.model_validate(bus)
    for branch in power["branches"]:
        PowerBranch.model_validate(branch)
    for generator in power["generators"]:
        Generator.model_validate(generator)
    for storage in power["storage"]:
        Storage.model_validate(storage)
    remote_assets = (
        [f"bus_{item['bus_id']}" for item in power["buses"]]
        + [item["branch_id"] for item in power["branches"]]
        + [item["generator_id"] for item in power["generators"]]
        + [item["storage_id"] for item in power["storage"]]
    )
    communication = build_communication_variants(comm_config, remote_assets)
    missions = build_missions(mission_config, communication)
    resources = build_resources(resource_config, communication)
    coupled = {
        "schema_version": "1.0", "system_id": system_id,
        "power": power, "communication": communication, "missions": missions, "restoration_resources": resources,
        "metadata": {
            "phase": 1, "root_seed": global_config["random_seed"],
            "derived_seeds": {name: seed_manager.child_seed(f"{system_id}:{name}") for name in [
                "system_augmentation", "communication_topology", "mission_assignment", "disruption_scenarios",
                "observation_masking", "restoration_resource_placement"]},
            "source": system_config["source"], "source_url": system_config["source_url"],
            "source_commit": system_config.get("source_commit", "package_version_pinned"),
            "source_hashes": _source_hashes(root_path, system_id),
            "candidate_disrupted_components": system_config["candidate_disrupted_components"],
            "availability_activation_rule": "activated <= available",
            "power_flow_model": system_config["power_flow_model"],
            "operating_windows": select_rts_windows(root_path) if system_id == "rts_gmlc" else ["intact_base"],
            "scope_exclusions": ["MANTLE quotient", "threat envelope", "external baseline", "comparative performance"],
        },
    }
    out = root_path / "data" / "modified" / system_id
    content_hash = write_json(out / "coupled_system.json", coupled)
    write_json(out / "communication_mapping.json", communication)
    write_json(out / "mission_mapping.json", missions)
    write_json(out / "restoration_resources.json", resources)
    write_json(out / "provenance.json", {"system_id": system_id, "coupled_system_sha256": content_hash,
                                                  "source_hashes": coupled["metadata"]["source_hashes"]})
    return coupled


def build_all_coupled_systems(root: str | Path) -> dict[str, str]:
    """Build all three required systems and return artifact hashes."""
    root_path = Path(root)
    hashes: dict[str, str] = {}
    for system_id in ["ieee14", "ieee39", "rts_gmlc"]:
        build_coupled_system(root_path, system_id)
        data = (root_path / "data" / "modified" / system_id / "coupled_system.json").read_bytes()
        hashes[system_id] = hashlib.sha256(data).hexdigest()
    return hashes
