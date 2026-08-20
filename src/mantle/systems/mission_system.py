"""Mission mapping and deterministic finite-state transitions."""

from __future__ import annotations

from typing import Any

from mantle.schemas.mission import Mission, MissionRuntime, MissionState


def build_missions(config: dict[str, Any], communication: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach each mission to valid power buses and canonical device terminals."""
    result: list[dict[str, Any]] = []
    endpoints = communication["canonical_endpoints"]
    for priority, item in enumerate(config["missions"], start=1):
        buses = [str(bus) for bus in item["mapped_power_buses"]]
        mapped_nodes = [endpoints[f"bus_{bus}"] for bus in buses]
        mission = Mission(
            mission_id=item["mission_id"], mission_name=item["mission_name"], mission_type=item["mission_type"],
            mapped_power_buses=buses, mapped_communication_nodes=mapped_nodes,
            minimum_power_requirement=item["minimum_power_requirement"],
            maximum_interruption_duration=item["maximum_interruption_duration"],
            minimum_recovery_duration=item["minimum_recovery_duration"],
            backup_energy_duration=item["backup_energy_duration"], dependency_type="power_and_communication" if item["communication_required"] else "power_primary",
            communication_required=item["communication_required"], priority_metadata={"ordinal": priority},
        )
        result.append(mission.model_dump(mode="json"))
    return result


def transition_mission(mission: Mission, runtime: MissionRuntime, served_power_ratio: float,
                       communication_available: bool) -> MissionRuntime:
    """Advance one time step under deterministic configured thresholds."""
    adequate = served_power_ratio >= mission.minimum_power_requirement and (communication_available or not mission.communication_required)
    full = served_power_ratio >= 1.0 and (communication_available or not mission.communication_required)
    previous = runtime.state
    if adequate:
        runtime.interruption_duration = 0
        if previous == MissionState.FAILED:
            runtime.state = MissionState.RECOVERING
            runtime.recovery_duration = 1
        elif previous == MissionState.RECOVERING:
            runtime.recovery_duration += 1
            runtime.state = MissionState.RESTORED if runtime.recovery_duration >= mission.minimum_recovery_duration else MissionState.RECOVERING
        elif previous == MissionState.RESTORED:
            runtime.state = MissionState.RESTORED
        else:
            runtime.state = MissionState.NORMAL if full else MissionState.DEGRADED
        return runtime
    runtime.recovery_duration = 0
    runtime.interruption_duration += 1
    if runtime.backup_remaining > 0:
        runtime.backup_remaining -= 1
    if runtime.interruption_duration > mission.maximum_interruption_duration or runtime.backup_remaining <= 0:
        runtime.state = MissionState.FAILED
    elif runtime.backup_remaining > 0:
        runtime.state = MissionState.BACKUP
    else:
        runtime.state = MissionState.DEGRADED
    return runtime


def initial_runtime(mission: Mission) -> MissionRuntime:
    """Create a NORMAL runtime with the configured backup duration."""
    return MissionRuntime(state=MissionState.NORMAL, backup_remaining=mission.backup_energy_duration)

