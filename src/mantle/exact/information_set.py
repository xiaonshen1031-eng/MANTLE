"""Exact information-set construction under complete and incomplete observation."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .state import ExactState


def canonical_information_set(states: Iterable[ExactState]) -> tuple[ExactState, ...]:
    """Deduplicate and lexicographically order hidden true states."""

    by_key = {state.discrete_key(): state for state in states}
    return tuple(by_key[key] for key in sorted(by_key, key=repr))


def build_information_set(states: Iterable[ExactState]) -> tuple[ExactState, ...]:
    """Build the canonical initial/current information set."""

    return canonical_information_set(states)


def update_information_set(
    successors: Iterable[ExactState],
) -> dict[tuple[object, ...], tuple[ExactState, ...]]:
    """Partition successors by exactly the public operator-visible key."""

    groups: dict[tuple[object, ...], list[ExactState]] = defaultdict(list)
    for successor in successors:
        groups[successor.public_key()].append(successor)
    return {
        key: canonical_information_set(groups[key])
        for key in sorted(groups, key=repr)
    }

