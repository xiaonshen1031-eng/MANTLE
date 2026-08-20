"""Feasibility-preserving resource and component transitions."""

from __future__ import annotations

from typing import Any


def start_repair(crew: dict[str, Any], asset: dict[str, Any], repair_time: float) -> None:
    """Occupy a free crew on one unavailable asset."""
    if crew["occupied_asset"] is not None:
        raise ValueError("crew is already occupied")
    if asset.get("available", True):
        raise ValueError("repair may start only on an unavailable asset")
    crew["occupied_asset"] = asset.get("branch_id") or asset.get("asset_id") or asset.get("comm_node_id")
    crew["remaining_repair_time"] = float(repair_time)


def progress_repair(crew: dict[str, Any], asset: dict[str, Any], hours: float) -> bool:
    """Advance repair; completion sets availability but never forces activation."""
    if crew["occupied_asset"] is None:
        raise ValueError("crew has no active repair")
    crew["remaining_repair_time"] = max(0.0, float(crew["remaining_repair_time"]) - float(hours))
    if crew["remaining_repair_time"] > 0:
        return False
    asset["available"] = True
    asset["activated"] = False
    crew["occupied_asset"] = None
    return True


def isolate_component(asset: dict[str, Any]) -> None:
    """Safely isolate an asset without changing physical availability."""
    asset["activated"] = False


def safe_reactivate(asset: dict[str, Any], delay_elapsed: bool, communication_or_local_control: bool) -> None:
    """Reactivate only an available component after delay and valid control authorization."""
    if not asset.get("available", False):
        raise ValueError("unavailable component cannot be activated")
    if not delay_elapsed:
        raise ValueError("reactivation delay has not elapsed")
    if not communication_or_local_control:
        raise ValueError("no valid remote or local control path")
    asset["activated"] = True


def relocate_mobile_storage(unit: dict[str, Any], destination: str) -> None:
    """Relocate one mobile unit while preserving its unique location."""
    if unit.get("connected", False):
        raise ValueError("connected storage must disconnect before relocation")
    if destination not in unit["travel_time_matrix"]:
        raise ValueError("destination is absent from travel-time matrix")
    unit["current_bus"] = destination


def deploy_emergency_communication(unit: dict[str, Any], node_id: str) -> None:
    """Deploy an available unit to one supported attachment point."""
    if not unit.get("available", False):
        raise ValueError("failed communication unit cannot be deployed")
    if unit.get("deployed_node") is not None:
        raise ValueError("communication unit is already deployed")
    if node_id not in unit["supported_nodes"]:
        raise ValueError("unsupported emergency attachment point")
    unit["deployed_node"] = node_id

