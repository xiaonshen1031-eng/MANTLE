"""Two-stage local grouping plus exact backward transition refinement."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .canonicalization import canonicalize
from .signature import mechanism_signature


def refine_partition(
    information_sets: dict[str, tuple[Any, ...]], edges: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the coarsest stable exact partition from ``chi`` and transitions."""

    signatures = {
        node_id: canonicalize(mechanism_signature(information))
        for node_id, information in information_sets.items()
    }
    local_groups: dict[Any, list[str]] = defaultdict(list)
    for node_id, signature in signatures.items():
        local_groups[signature].append(node_id)
    classes: dict[str, int] = {}
    for class_id, signature in enumerate(sorted(local_groups, key=repr)):
        for node_id in sorted(local_groups[signature]):
            classes[node_id] = class_id
    iterations = 0
    while True:
        iterations += 1
        outgoing: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
        for edge in edges:
            outgoing[edge["source"]].append(
                (edge["operator_action"], edge["observation"], classes[edge["target"]])
            )
        keys = {
            node_id: (
                signatures[node_id],
                tuple(sorted(outgoing.get(node_id, []))),
            )
            for node_id in information_sets
        }
        groups: dict[Any, list[str]] = defaultdict(list)
        for node_id, key in keys.items():
            groups[key].append(node_id)
        updated: dict[str, int] = {}
        for class_id, key in enumerate(sorted(groups, key=repr)):
            for node_id in sorted(groups[key]):
                updated[node_id] = class_id
        if all(updated[node_id] == classes[node_id] for node_id in classes):
            classes = updated
            break
        classes = updated
    members: dict[int, list[str]] = defaultdict(list)
    for node_id, class_id in classes.items():
        members[class_id].append(node_id)
    return {
        "iterations": iterations,
        "local_group_count": len(local_groups),
        "class_of": classes,
        "classes": {
            str(class_id): sorted(node_ids) for class_id, node_ids in sorted(members.items())
        },
    }

