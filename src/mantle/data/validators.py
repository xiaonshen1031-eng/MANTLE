"""Coupled-system acceptance validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mantle.schemas.communication import CommunicationLink, CommunicationNode
from mantle.schemas.mission import Mission, MissionState
from mantle.schemas.power import Generator, PowerBranch, PowerBus, Storage
from mantle.systems.communication_system import reachable_endpoints
from mantle.systems.power_system import select_rts_windows, validate_power_flow
from mantle.utilities.serialization import read_json, sha256_value, write_json


def validate_coupled_system(root: str | Path, system_id: str) -> dict[str, Any]:
    """Validate referential integrity, AC flow, reachability, resources, and serialization."""
    root_path = Path(root)
    path = root_path / "data" / "modified" / system_id / "coupled_system.json"
    data = read_json(path)
    buses = [PowerBus.model_validate(x) for x in data["power"]["buses"]]
    branches = [PowerBranch.model_validate(x) for x in data["power"]["branches"]]
    generators = [Generator.model_validate(x) for x in data["power"]["generators"]]
    storage = [Storage.model_validate(x) for x in data["power"]["storage"]]
    bus_ids = [x.bus_id for x in buses]
    unique_ids = len(bus_ids) == len(set(bus_ids)) and len({x.branch_id for x in branches}) == len(branches)
    valid_refs = all(x.from_bus in bus_ids and x.to_bus in bus_ids for x in branches)
    valid_refs &= all(x.bus_id in bus_ids for x in generators + storage)
    nodes = [CommunicationNode.model_validate(x) for x in data["communication"]["nodes"]]
    links = [CommunicationLink.model_validate(x) for x in data["communication"]["variants"]["meshed"]]
    node_ids = {x.comm_node_id for x in nodes}
    valid_refs &= all(x.from_node in node_ids and x.to_node in node_ids for x in links)
    reached = reachable_endpoints(data["communication"])
    required = set(data["communication"]["canonical_endpoints"].values())
    canonical_unique = len(data["communication"]["canonical_endpoints"]) == len(set(data["communication"]["canonical_endpoints"].values()))
    missions = [Mission.model_validate(x) for x in data["missions"]]
    mission_valid = all(set(m.mapped_power_buses) <= set(bus_ids) and set(m.mapped_communication_nodes) <= node_ids
                        and m.initial_state == MissionState.NORMAL for m in missions)
    resource_ids = []
    for category in ["repair_crews", "mobile_storage", "emergency_communication_units", "black_start_resources"]:
        for item in data["restoration_resources"][category]:
            resource_ids.append(item.get("crew_id") or item.get("unit_id") or item.get("resource_id"))
    resources_unique = len(resource_ids) == len(set(resource_ids))
    flows = [validate_power_flow(root_path, system_id)] if system_id != "rts_gmlc" else [
        validate_power_flow(root_path, system_id, window) for window in select_rts_windows(root_path)
    ]
    canonical_hash = sha256_value(data)
    reload_equal = read_json(path) == data
    result = {
        "system_id": system_id, "counts": {
            "buses": len(buses), "branches": len(branches), "generators": len(generators),
            "renewable_units": sum(g.renewable for g in generators), "loads": sum(b.load_p > 0 for b in buses),
            "storage_units": len(storage) + len(data["restoration_resources"]["mobile_storage"]),
            "communication_nodes": len(nodes), "communication_links": len(links), "missions": len(missions),
            "repair_crews": len(data["restoration_resources"]["repair_crews"]),
            "emergency_communication_units": len(data["restoration_resources"]["emergency_communication_units"]),
            "candidate_disrupted_assets": len(data["metadata"]["candidate_disrupted_components"]),
        },
        "checks": {
            "unique_power_ids": unique_ids, "all_references_valid": valid_refs,
            "all_required_endpoints_reachable": required <= reached, "canonical_endpoints_unique": canonical_unique,
            "power_dependency_documented": all(bool(n.power_supply_bus) for n in nodes),
            "backup_duration_documented": all(n.backup_power_duration >= 0 for n in nodes),
            "local_autonomy_present": any(n.local_autonomy_capability for n in nodes),
            "missions_valid_and_normal": mission_valid, "resources_unique": resources_unique,
            "serialization_reload_equal": reload_equal, "activation_implies_availability": all(not b.activated or b.available for b in branches),
        },
        "power_flow": flows, "canonical_sha256": canonical_hash,
    }
    result["passed"] = all(result["checks"].values()) and all(
        f["converged"] and f["balance_residual_mw"] <= 1e-6 and f["line_limit_violations"] == 0
        and f["transformer_limit_violations"] == 0 and f["generator_limit_violations"] == 0 for f in flows
    )
    write_json(root_path / "results" / "phase1" / "validation" / f"{system_id}_validation.json", result)
    return result


def validate_all(root: str | Path) -> dict[str, Any]:
    """Validate all required systems and write a consolidated report."""
    results = {sid: validate_coupled_system(root, sid) for sid in ["ieee14", "ieee39", "rts_gmlc"]}
    summary = {"passed": all(item["passed"] for item in results.values()), "systems": results}
    write_json(Path(root) / "results" / "phase1" / "validation" / "validation_summary.json", summary)
    return summary
