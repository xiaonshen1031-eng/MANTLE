"""Stage/budget-indexed exact losing sets from the minimax fixed point."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_failure_sets(nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Collect every and only nodes with terminal mission-failure value one."""

    groups: dict[tuple[int, int], list[str]] = defaultdict(list)
    for node_id, node in nodes.items():
        if int(node["value"][0]) == 1:
            groups[(int(node["stage"]), int(node["budget"]))].append(node_id)
    return {
        "by_stage_budget": {
            f"t{stage}_b{budget}": sorted(ids)
            for (stage, budget), ids in sorted(groups.items())
        },
        "all_failure_ids": sorted({item for ids in groups.values() for item in ids}),
    }

