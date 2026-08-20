"""Canonical mechanism signature ``chi=(q,b,C,E,T)``."""

from __future__ import annotations

from typing import Any

from mantle.exact.state import COMPONENTS, ExactState

from .capability import construct_capability


def mechanism_signature(information: tuple[ExactState, ...]) -> dict[str, Any]:
    """Build the full mission/budget/capability/exposure/transition signature."""

    q = tuple(
        tuple(
            (mission.state, mission.interruption, mission.backup_used, mission.recovery)
            for mission in state.missions
        )
        for state in information
    )
    exposures = tuple(
        sorted(
            COMPONENTS[index]
            for index in range(len(COMPONENTS))
            if any(state.activation[index] for state in information)
        )
    )
    transitions = tuple(
        sorted(
            {
                (state.observation, state.controllability, state.resources)
                for state in information
            },
            key=repr,
        )
    )
    return {
        "q": q,
        "b": information[0].budget,
        "C": construct_capability(information),
        "E": exposures,
        "T": transitions,
    }

