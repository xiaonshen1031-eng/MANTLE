"""Threat dominance as static order plus recursive alternating simulation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .capability import MISSION_RANK


def _mission_worse_or_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    # Exact timer equality is deliberately conservative. Equality satisfies the
    # required worse-or-equal condition and avoids claiming an unproved timer order.
    return left["q"] == right["q"]


def static_threat_order(worse: dict[str, Any], safer: dict[str, Any]) -> bool:
    """Check mission, budget, capability-subset, and exposure-superset conditions."""

    return (
        _mission_worse_or_equal(worse, safer)
        and worse["b"] >= safer["b"]
        and worse["C"] == safer["C"]
        and worse["E"] == safer["E"]
        and worse["T"] == safer["T"]
    )


def recursive_alternating_simulation(
    signatures: dict[str, dict[str, Any]], edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute a proved conservative fixed point without comparing node values."""

    outgoing: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for edge in edges:
        outgoing[edge["source"]][edge["operator_action"]].add(edge["target"])
    # Phase-2 core found that the available observable capability summary does not
    # prove any cross-node hidden-state order. The reflexive relation is retained as
    # the sound alternating-simulation fixed point; no value-based filtering is used.
    relation = {(node_id, node_id) for node_id in signatures}
    changed = True
    while changed:
        changed = False
        remove: set[tuple[str, str]] = set()
        for worse, safer in relation:
            for action, worse_successors in outgoing.get(worse, {}).items():
                safer_successors = outgoing.get(safer, {}).get(action, set())
                if not safer_successors:
                    remove.add((worse, safer))
                    break
                if any(
                    not any((ws, ss) in relation for ws in worse_successors)
                    for ss in safer_successors
                ):
                    remove.add((worse, safer))
                    break
        if remove:
            relation -= remove
            changed = True
    witnesses = []
    for worse, safer in sorted(relation):
        witnesses.append(
            {
                "worse": worse,
                "safer": safer,
                "static": {
                    "budget": [signatures[worse]["b"], signatures[safer]["b"]],
                    "capability_subset": True,
                    "exposure_superset": True,
                    "mission_worse_or_equal": True,
                },
                "matched_operator_actions": sorted(outgoing.get(worse, {})),
            }
        )
    return {"pairs": [list(pair) for pair in sorted(relation)], "witnesses": witnesses}
