"""Minimal failing antichain under audited threat dominance."""

from __future__ import annotations


def minimal_antichain(failure_ids: set[str], dominance_pairs: set[tuple[str, str]]) -> list[str]:
    """Remove a worse failure when a distinct safer failing mechanism generates it."""

    return sorted(
        node
        for node in failure_ids
        if not any(
            worse == node and safer in failure_ids and safer != node
            for worse, safer in dominance_pairs
        )
    )


def reconstruct_upward_closure(
    antichain: set[str], dominance_pairs: set[tuple[str, str]]
) -> set[str]:
    """Reconstruct the exact upward closure including reflexive membership."""

    closure = set(antichain)
    changed = True
    while changed:
        changed = False
        for worse, safer in dominance_pairs:
            if safer in closure and worse not in closure:
                closure.add(worse)
                changed = True
    return closure

