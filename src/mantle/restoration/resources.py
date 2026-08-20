"""Construct configured resource inventories."""

from __future__ import annotations

from typing import Any

from mantle.schemas.restoration import BlackStartResource, EmergencyCommunicationUnit, MobileStorageUnit, RepairCrew


def build_resources(config: dict[str, Any], communication: dict[str, Any]) -> dict[str, Any]:
    """Build unique, valid initial resource states from YAML."""
    system_id = config["system_id"]
    crews = [RepairCrew(
        crew_id=f"{system_id}_crew_{idx+1}", initial_location=str(location), current_location=str(location),
        travel_speed=50.0, eligible_asset_types=["bus", "branch", "generator", "communication_node", "communication_link"],
        repair_capacity=1,
    ) for idx, location in enumerate(config["crew_locations"])]
    mobile_storage = [MobileStorageUnit(
        unit_id=f"{system_id}_mobile_storage_{idx+1}", initial_bus=str(bus), current_bus=str(bus),
        energy_capacity=100.0, power_capacity=25.0,
        travel_time_matrix={str(other): float(config["travel_time_hours"]) for other in config["storage_buses"]},
    ) for idx, bus in enumerate(config["storage_buses"])]
    supported = [node["comm_node_id"] for node in communication["nodes"] if node["emergency_attachment_point"]]
    emergency = [EmergencyCommunicationUnit(
        unit_id=f"{system_id}_ecu_{idx+1}", initial_location=str(config["crew_locations"][idx % len(config["crew_locations"])]),
        current_location=str(config["crew_locations"][idx % len(config["crew_locations"])]),
        deployment_time=float(config["travel_time_hours"]), supported_nodes=supported, operating_duration=12.0,
    ) for idx in range(int(config["emergency_communication_count"]))]
    black_start = [BlackStartResource(
        resource_id=f"{system_id}_black_start_{idx+1}", generator_id=str(generator), startup_time=2.0,
        startup_energy=5.0, initial_availability=True,
    ) for idx, generator in enumerate(config["black_start_resources"])]
    return {
        "repair_crews": [x.model_dump(mode="json") for x in crews],
        "mobile_storage": [x.model_dump(mode="json") for x in mobile_storage],
        "emergency_communication_units": [x.model_dump(mode="json") for x in emergency],
        "black_start_resources": [x.model_dump(mode="json") for x in black_start],
        "reactivation_delay_hours": float(config["reactivation_delay_hours"]),
        "local_autonomous_controllers": [n["comm_node_id"] for n in communication["nodes"] if n["local_autonomy_capability"]],
    }

