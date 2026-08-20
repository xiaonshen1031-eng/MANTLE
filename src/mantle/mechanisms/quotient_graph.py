"""Build a deterministic quotient graph from an audited stable partition."""

from __future__ import annotations

from typing import Any


def build_quotient_graph(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    partition: dict[str, Any],
) -> dict[str, Any]:
    """Map exact information nodes and labeled edges to equivalence classes."""

    class_of = partition["class_of"]
    quotient_nodes = []
    for class_id, members in sorted(partition["classes"].items(), key=lambda row: int(row[0])):
        values = [nodes[member]["value"] for member in members]
        quotient_nodes.append(
            {
                "class_id": int(class_id),
                "members": members,
                "class_size": len(members),
                "value": min(values),
                "value_span": [min(values), max(values)],
            }
        )
    quotient_edges = sorted(
        {
            (
                class_of[edge["source"]],
                class_of[edge["target"]],
                edge["operator_action"],
                edge["observation"],
            )
            for edge in edges
        }
    )
    return {
        "nodes": quotient_nodes,
        "edges": [
            {
                "source": source,
                "target": target,
                "operator_action": action,
                "observation": observation,
            }
            for source, target, action, observation in quotient_edges
        ],
    }

