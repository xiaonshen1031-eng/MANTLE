"""Safe policy certificate for every budget strictly below Gamma."""

from __future__ import annotations

from typing import Any


def safe_policy_certificate(
    gamma: int, policies: dict[int, dict[str, str]], values: dict[int, list[float | int]]
) -> dict[str, Any]:
    """Retain initial values and common-action policies for ``b < Gamma``."""

    return {
        "gamma": gamma,
        "certified_budgets": list(range(gamma)),
        "initial_values": {str(b): values[b] for b in range(gamma)},
        "policies": {str(b): policies[b] for b in range(gamma)},
        "all_safe": all(int(values[b][0]) == 0 for b in range(gamma)),
    }

