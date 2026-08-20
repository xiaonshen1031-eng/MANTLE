"""Failure-envelope certificate at the critical survivability budget."""

from __future__ import annotations

from typing import Any


def failure_mechanism_certificate(
    gamma: int, envelope: dict[str, Any], failing_histories: list[dict[str, Any]]
) -> dict[str, Any]:
    """Link critical-budget failures to retained histories and envelope generators."""

    return {
        "gamma": gamma,
        "envelope_mechanisms": envelope["minimal_failing_mechanisms"],
        "failing_history_count": len(failing_histories),
        "failing_histories": failing_histories,
        "closure_exact": envelope["exact_match"],
    }

