"""Universal-operator/existential-disruption failure predecessor audit."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def failure_predecessor(
    node_id: str,
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    failure_ids: set[str],
) -> tuple[bool, dict[str, str]]:
    """Check ``forall operator action, exists a failing successor`` and witness it."""

    by_action: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["source"] == node_id:
            by_action[edge["operator_action"]].append(edge["target"])
    if nodes[node_id].get("terminal"):
        return node_id in failure_ids, {"terminal": node_id}
    witnesses: dict[str, str] = {}
    for action, targets in sorted(by_action.items()):
        failing_targets = sorted(set(targets) & failure_ids)
        if not failing_targets:
            return False, witnesses
        witnesses[action] = failing_targets[0]
    return bool(by_action), witnesses

