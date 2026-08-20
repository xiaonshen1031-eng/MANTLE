"""Memoized exact information-state DP used to construct the MANTLE quotient."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from .actions import enumerate_disruptions, enumerate_nonanticipative_actions
from .information_set import canonical_information_set, update_information_set
from .state import ExactState
from .transition import apply_transition
from .value import GameValue, terminal_value


@dataclass
class MantleResult:
    """Worst and state-conditioned values at one exact information node."""

    worst: GameValue
    per_state: dict[tuple[Any, ...], GameValue]


class MantleExactSolver:
    """Exact DP with memoization only; mechanism reduction is audited post-graph."""

    def __init__(self, horizon: int):
        self.horizon = horizon
        self.cache: dict[tuple[Any, ...], MantleResult] = {}
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.policy: dict[str, str] = {}
        self.information_sets: dict[str, tuple[ExactState, ...]] = {}
        self.runtime_seconds = 0.0
        self.cache_hits = 0

    @staticmethod
    def information_key(information: tuple[ExactState, ...]) -> tuple[Any, ...]:
        """Canonical exact key; this is memoization, not theorem-based pruning."""

        return tuple(state.discrete_key() for state in information)

    @staticmethod
    def mechanism_id(key: tuple[Any, ...]) -> str:
        """Return a deterministic identifier without serializing hidden labels."""

        return "M" + hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:12]

    def solve(self, initial_information: tuple[ExactState, ...]) -> MantleResult:
        """Solve all exact information states reachable under every legal action."""

        start = time.perf_counter()
        result = self._visit(canonical_information_set(initial_information))
        self.runtime_seconds = time.perf_counter() - start
        return result

    def _visit(self, information: tuple[ExactState, ...]) -> MantleResult:
        key = self.information_key(information)
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        mechanism_id = self.mechanism_id(key)
        self.information_sets[mechanism_id] = information
        stage = information[0].t
        if stage >= self.horizon:
            per_state = {state.discrete_key(): terminal_value(state) for state in information}
            result = MantleResult(max(per_state.values()), per_state)
            self.cache[key] = result
            self.nodes[mechanism_id] = {
                "mechanism_id": mechanism_id,
                "stage": stage,
                "budget": information[0].budget,
                "information_cardinality": len(information),
                "terminal": True,
                "value": result.worst.to_list(),
            }
            return result

        actions, audit = enumerate_nonanticipative_actions(information)
        action_results: list[tuple[GameValue, str, dict[tuple[Any, ...], GameValue]]] = []
        for action in actions:
            entries: list[tuple[ExactState, ExactState, tuple[float, float, float, float]]] = []
            successors: list[ExactState] = []
            for state in information:
                for disruption in enumerate_disruptions(state):
                    successor, cost = apply_transition(state, action, disruption)
                    entries.append((state, successor, cost))
                    successors.append(successor)
            continuation: dict[tuple[Any, ...], GameValue] = {}
            for public_key, child_information in update_information_set(successors).items():
                child = self._visit(child_information)
                child_key = self.information_key(child_information)
                child_id = self.mechanism_id(child_key)
                continuation.update(child.per_state)
                self.edges.append(
                    {
                        "source": mechanism_id,
                        "target": child_id,
                        "operator_action": action.action_id,
                        "observation": hashlib.sha256(repr(public_key).encode("utf-8")).hexdigest()[:10],
                    }
                )
            current_values: dict[tuple[Any, ...], GameValue] = {}
            for state in information:
                current_values[state.discrete_key()] = max(
                    continuation[successor.discrete_key()].add_stage(cost)
                    for parent, successor, cost in entries
                    if parent.discrete_key() == state.discrete_key()
                )
            action_results.append((max(current_values.values()), action.action_id, current_values))
        selected = min(action_results, key=lambda row: (row[0], row[1]))
        result = MantleResult(selected[0], selected[2])
        self.cache[key] = result
        self.policy[mechanism_id] = selected[1]
        self.nodes[mechanism_id] = {
            "mechanism_id": mechanism_id,
            "stage": stage,
            "budget": information[0].budget,
            "information_cardinality": len(information),
            "terminal": False,
            "candidate_actions": audit["candidate_count"],
            "rejected_actions": audit["rejected_count"],
            "feasible_common_actions": len(actions),
            "selected_action": selected[1],
            "value": selected[0].to_list(),
        }
        return result

    def summary(self, value: GameValue) -> dict[str, Any]:
        """Return quotient-construction metrics before theorem refinement."""

        return {
            "algorithm": "mantle_exact_information_state_dp",
            "horizon": self.horizon,
            "value": value.to_list(),
            "information_nodes": len(self.nodes),
            "cache_hits": self.cache_hits,
            "runtime_seconds": round(self.runtime_seconds, 8),
            "policy": dict(sorted(self.policy.items())),
        }

