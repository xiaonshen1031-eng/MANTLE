"""Exact threat-envelope construction and closure precision/recall."""

from __future__ import annotations

from typing import Any

from .antichain import minimal_antichain, reconstruct_upward_closure


def build_threat_envelope(
    failure_ids: set[str], dominance_pairs: set[tuple[str, str]]
) -> dict[str, Any]:
    """Build a minimal generator set and verify its closure against failures."""

    antichain = set(minimal_antichain(failure_ids, dominance_pairs))
    reconstructed = reconstruct_upward_closure(antichain, dominance_pairs)
    true_positive = len(reconstructed & failure_ids)
    precision = true_positive / len(reconstructed) if reconstructed else 1.0
    recall = true_positive / len(failure_ids) if failure_ids else 1.0
    return {
        "minimal_failing_mechanisms": sorted(antichain),
        "reconstructed_failure_ids": sorted(reconstructed),
        "precision": precision,
        "recall": recall,
        "exact_match": reconstructed == failure_ids,
    }

