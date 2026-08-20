"""Robust capabilities computed over complete or non-singleton information sets."""

from __future__ import annotations

from typing import Any

from mantle.exact.actions import enumerate_nonanticipative_actions
from mantle.exact.state import ExactState


MISSION_RANK = {
    "NORMAL": 0,
    "RECOVERING": 1,
    "BACKUP": 2,
    "DEGRADED": 3,
    "INTERRUPTED": 4,
    "FAILED": 5,
}


def construct_capability(information: tuple[ExactState, ...]) -> tuple[dict[str, Any], ...]:
    """Construct observable robust guarantees without flows or hidden-state IDs."""

    actions, _ = enumerate_nonanticipative_actions(information)
    capabilities: list[dict[str, Any]] = []
    for action in actions:
        mission_guarantee = tuple(
            max(MISSION_RANK[state.missions[index].state] for state in information)
            for index in range(len(information[0].missions))
        )
        activation = []
        for index in range(len(information[0].activation)):
            values = {state.activation[index] for state in information}
            activation.append(next(iter(values)) if len(values) == 1 else "unknown")
        capabilities.append(
            {
                "action_id": action.action_id,
                "guaranteed_mission_vector": mission_guarantee,
                "resource_successor": (
                    information[0].resources.emergency_comm,
                    information[0].resources.local_autonomy,
                    action.kind,
                ),
                "activation_successor": tuple(activation),
                "rule_id": f"robust_{action.kind}",
            }
        )
    return tuple(sorted(capabilities, key=lambda row: row["action_id"]))

