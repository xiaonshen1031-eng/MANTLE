"""Finite restoration and disruption action spaces with robust feasibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .state import COMPONENTS, ExactState, OBS_UNKNOWN


@dataclass(frozen=True, order=True)
class RestorationAction:
    """Common operator action applied to every state in an information set."""

    action_id: str
    kind: str
    target: str = ""


@dataclass(frozen=True, order=True)
class DisruptionAction:
    """Adversary action with an abstract integer budget cost."""

    action_id: str
    kind: str
    target: str = ""
    cost: int = 1


def enumerate_disruptions(state: ExactState) -> tuple[DisruptionAction, ...]:
    """Enumerate every legal disruption without heuristic pruning."""

    actions = [DisruptionAction("D00_noop", "noop", cost=0)]
    if state.budget <= 0:
        return tuple(actions)
    remote_exposure = bool(state.availability[4] and state.activation[4])
    for index, target in enumerate(COMPONENTS):
        if index < 4 and not remote_exposure:
            continue
        if state.availability[index] and state.activation[index]:
            actions.append(DisruptionAction(f"D10_fail_{target}", "fail", target))
    actions.append(DisruptionAction("D20_degrade_obs_branch_0", "degrade_observation", "branch_0"))
    return tuple(sorted(actions))


def _robustly_feasible(states: tuple[ExactState, ...], action: RestorationAction) -> bool:
    if action.kind == "wait":
        return True
    if action.kind == "repair":
        index = COMPONENTS.index(action.target)
        return all(state.resources.repair_remaining == 0 for state in states) and any(
            state.availability[index] == 0 or state.observation[index] == OBS_UNKNOWN
            for state in states
        )
    if action.kind == "repair_activate":
        index = COMPONENTS.index(action.target)
        return all(state.resources.repair_remaining == 0 for state in states) and any(
            state.availability[index] == 0 or state.observation[index] == OBS_UNKNOWN
            for state in states
        )
    if action.kind == "isolate":
        index = COMPONENTS.index(action.target)
        return all(state.activation[index] == 1 for state in states) and any(
            state.observation[index] == OBS_UNKNOWN for state in states
        )
    if action.kind == "activate":
        index = COMPONENTS.index(action.target)
        return all(
            state.availability[index] == 1 and state.activation[index] == 0
            for state in states
        )
    if action.kind == "deploy_emergency_comm":
        return all(state.resources.emergency_comm == 0 for state in states) and any(
            state.availability[4] == 0 or state.availability[5] == 0 for state in states
        )
    if action.kind == "enable_local_autonomy":
        return all(state.resources.local_autonomy == 0 for state in states) and any(
            state.controllability[0] == "none" for state in states
        )
    return False


def enumerate_nonanticipative_actions(
    info_state: Iterable[ExactState],
) -> tuple[tuple[RestorationAction, ...], dict[str, int]]:
    """Return actions feasible for all hidden states and rejection counts."""

    states = tuple(sorted(info_state, key=ExactState.discrete_key))
    candidates: list[RestorationAction] = [RestorationAction("R00_wait", "wait")]
    for target in COMPONENTS:
        candidates.append(RestorationAction(f"R10_repair_{target}", "repair", target))
        candidates.append(
            RestorationAction(f"R11_repair_activate_{target}", "repair_activate", target)
        )
    for target in ("branch_0", "branch_1", "ieee14_MAIN", "ieee14_FIELD_3"):
        candidates.append(RestorationAction(f"R20_isolate_{target}", "isolate", target))
        candidates.append(RestorationAction(f"R30_activate_{target}", "activate", target))
    candidates.extend(
        [
            RestorationAction("R40_deploy_emergency_comm", "deploy_emergency_comm"),
            RestorationAction("R50_enable_local_autonomy", "enable_local_autonomy"),
        ]
    )
    accepted = tuple(action for action in sorted(candidates) if _robustly_feasible(states, action))
    return accepted, {
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "rejected_count": len(candidates) - len(accepted),
    }
