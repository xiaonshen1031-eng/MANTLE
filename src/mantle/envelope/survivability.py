"""Initial-state survivability index from exact budget-indexed values."""

from __future__ import annotations

from typing import Any


def survivability_index(values_by_budget: dict[int, list[float | int]]) -> int | None:
    """Return the least abstract budget that forces mission failure."""

    for budget in sorted(values_by_budget):
        if int(values_by_budget[budget][0]) == 1:
            return budget
    return None


def survivability_summary(
    fhtdp_values: dict[int, list[float | int]], mantle_values: dict[int, list[float | int]]
) -> dict[str, Any]:
    """Compare exact integer Gamma values from both implementations."""

    fhtdp_gamma = survivability_index(fhtdp_values)
    mantle_gamma = survivability_index(mantle_values)
    return {
        "gamma_fhtdp": fhtdp_gamma,
        "gamma_mantle": mantle_gamma,
        "exact_integer_match": fhtdp_gamma == mantle_gamma,
    }

