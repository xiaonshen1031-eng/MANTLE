"""Typed discrete state for the frozen IEEE-14 exact restoration game."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


COMPONENTS = (
    "branch_0",
    "branch_1",
    "gen_0",
    "bus_3",
    "ieee14_MAIN",
    "ieee14_FIELD_3",
)
MISSION_IDS = (
    "ieee14_medical",
    "ieee14_emcomm",
    "ieee14_water",
    "ieee14_command",
)
OBS_UNKNOWN = -1
OBS_FAILED = 0
OBS_HEALTHY = 1
OBS_DELAYED_HEALTHY = 2


@dataclass(frozen=True, order=True)
class MissionRuntime:
    """Six-state mission automaton state and its explicit timers."""

    state: str = "NORMAL"
    interruption: int = 0
    backup_used: int = 0
    recovery: int = 0


@dataclass(frozen=True, order=True)
class ResourceState:
    """Observable crew and emergency-resource state."""

    crew_target: str = ""
    repair_remaining: int = 0
    emergency_comm: int = 0
    local_autonomy: int = 0


@dataclass(frozen=True, order=True)
class ExactState:
    """State ``(x,v,e,o,c,r,q,b)`` with no continuous solver variables."""

    t: int
    availability: tuple[int, ...]
    activation: tuple[int, ...]
    observation: tuple[int, ...]
    controllability: tuple[str, ...]
    resources: ResourceState
    missions: tuple[MissionRuntime, ...]
    budget: int

    def discrete_key(self) -> tuple[Any, ...]:
        """Return the deterministic hash key, excluding DC continuous solutions."""

        return (
            self.t,
            self.availability,
            self.activation,
            self.observation,
            self.controllability,
            self.resources,
            self.missions,
            self.budget,
        )

    def public_key(self) -> tuple[Any, ...]:
        """Return the information available to the operator."""

        return (
            self.t,
            self.observation,
            self.controllability,
            self.resources,
            self.missions,
            self.budget,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the state without exposing noncanonical Python objects."""

        value = asdict(self)
        value["components"] = list(COMPONENTS)
        value["mission_ids"] = list(MISSION_IDS)
        return value


def derive_controllability(
    availability: tuple[int, ...], resources: ResourceState
) -> tuple[str, ...]:
    """Derive remote/local/none control from activated communications/resources."""

    main_up = bool(availability[4]) or bool(resources.emergency_comm)
    field_up = bool(availability[5]) or bool(resources.emergency_comm)
    control: list[str] = []
    for index, _ in enumerate(COMPONENTS):
        if main_up and (field_up or index in (4, 5)):
            control.append("remote")
        elif resources.local_autonomy:
            control.append("local")
        else:
            control.append("none")
    return tuple(control)


def initial_state(budget: int = 0) -> ExactState:
    """Create the accepted all-healthy IEEE-14 Phase-2 initial state."""

    availability = (1,) * len(COMPONENTS)
    resources = ResourceState()
    return ExactState(
        t=0,
        availability=availability,
        activation=availability,
        observation=(OBS_HEALTHY,) * len(COMPONENTS),
        controllability=derive_controllability(availability, resources),
        resources=resources,
        missions=tuple(MissionRuntime() for _ in MISSION_IDS),
        budget=budget,
    )

