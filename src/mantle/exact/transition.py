"""Frozen Phase-2 event order and mission/resource transition semantics."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .actions import DisruptionAction, RestorationAction
from .feasibility_oracle import solve_stage_feasibility
from .state import (
    COMPONENTS,
    MISSION_IDS,
    ExactState,
    MissionRuntime,
    OBS_DELAYED_HEALTHY,
    OBS_FAILED,
    OBS_HEALTHY,
    OBS_UNKNOWN,
    ResourceState,
    derive_controllability,
)


ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def _mission_parameters() -> dict[str, dict[str, object]]:
    path = ROOT / "data" / "modified" / "ieee14" / "mission_mapping.json"
    with path.open("r", encoding="utf-8") as handle:
        return {row["mission_id"]: row for row in json.load(handle)}


def _update_mission(
    runtime: MissionRuntime, ratio: float, communication: bool, parameters: dict[str, object]
) -> MissionRuntime:
    if runtime.state == "FAILED":
        return runtime
    service_ok = ratio + 1.0e-7 >= float(parameters["minimum_power_requirement"]) and communication
    if service_ok:
        if runtime.state == "NORMAL":
            return MissionRuntime()
        recovery = runtime.recovery + 1
        if recovery >= int(parameters["minimum_recovery_duration"]):
            return MissionRuntime()
        return MissionRuntime("RECOVERING", 0, runtime.backup_used, recovery)
    interruption = runtime.interruption + 1
    backup_used = runtime.backup_used + 1
    if interruption > int(parameters["maximum_interruption_duration"]):
        return MissionRuntime("FAILED", interruption, backup_used, 0)
    if backup_used <= int(parameters["backup_energy_duration"]):
        return MissionRuntime("BACKUP", interruption, backup_used, 0)
    return MissionRuntime("INTERRUPTED", interruption, backup_used, 0)


def apply_transition(
    state: ExactState,
    restoration_action: RestorationAction,
    disruption_action: DisruptionAction,
) -> tuple[ExactState, tuple[float, float, float, float]]:
    """Apply the documented 11-step event order and return successor plus stage cost."""

    availability = list(state.availability)
    activation = list(state.activation)
    budget = state.budget - disruption_action.cost

    # Steps 3-4: adversary action and true-state update.
    if disruption_action.kind == "fail":
        index = COMPONENTS.index(disruption_action.target)
        availability[index] = 0
        activation[index] = 0

    # Step 5: observation is generated before repair completion.
    observation = [OBS_HEALTHY if value else OBS_FAILED for value in availability]
    if disruption_action.kind == "degrade_observation":
        observation[COMPONENTS.index(disruption_action.target)] = OBS_UNKNOWN
    if disruption_action.kind == "fail" and disruption_action.target == "branch_0":
        observation[COMPONENTS.index("branch_0")] = OBS_UNKNOWN

    # Steps 6-7: resource progress and repair set availability only.
    resources = state.resources
    repair_target = ""
    if restoration_action.kind in {"repair", "repair_activate"}:
        repair_target = restoration_action.target
        repair_index = COMPONENTS.index(repair_target)
        availability[repair_index] = 1
        observation[repair_index] = OBS_DELAYED_HEALTHY
        resources = ResourceState(
            crew_target="",
            repair_remaining=0,
            emergency_comm=resources.emergency_comm,
            local_autonomy=resources.local_autonomy,
        )
    if restoration_action.kind == "deploy_emergency_comm":
        resources = ResourceState(
            resources.crew_target,
            resources.repair_remaining,
            1,
            resources.local_autonomy,
        )
    if restoration_action.kind == "enable_local_autonomy":
        resources = ResourceState(
            resources.crew_target,
            resources.repair_remaining,
            resources.emergency_comm,
            1,
        )

    # Step 8: activation changes only under an explicit action.
    if restoration_action.kind == "isolate":
        activation[COMPONENTS.index(restoration_action.target)] = 0
    elif restoration_action.kind == "activate":
        activation[COMPONENTS.index(restoration_action.target)] = 1
    elif restoration_action.kind == "repair_activate":
        activation[COMPONENTS.index(restoration_action.target)] = 1
    for index in range(len(activation)):
        activation[index] = int(bool(activation[index] and availability[index]))

    intermediate = ExactState(
        t=state.t + 1,
        availability=tuple(availability),
        activation=tuple(activation),
        observation=tuple(observation),
        controllability=derive_controllability(tuple(availability), resources),
        resources=resources,
        missions=state.missions,
        budget=budget,
    )
    # Steps 9-10: frozen DC oracle followed by all four mission automata.
    oracle = solve_stage_feasibility(intermediate, restoration_action)
    inputs = {mission_id: (ratio, comm) for mission_id, ratio, comm in oracle.mission_inputs}
    parameters = _mission_parameters()
    missions = tuple(
        _update_mission(state.missions[index], *inputs[mission_id], parameters[mission_id])
        for index, mission_id in enumerate(MISSION_IDS)
    )
    successor = ExactState(
        t=intermediate.t,
        availability=intermediate.availability,
        activation=intermediate.activation,
        observation=intermediate.observation,
        controllability=intermediate.controllability,
        resources=intermediate.resources,
        missions=missions,
        budget=intermediate.budget,
    )
    return successor, oracle.objective_components
