"""Complete/incomplete observation generation with linked truth."""

from __future__ import annotations

from typing import Any
import hashlib

import numpy as np

from mantle.schemas.observation import ObservationRecord


def _observation_id(system_id: str, scenario_id: str, mode: str, seed: int) -> str:
    """Build a stable observation identifier."""
    return hashlib.sha256(f"{system_id}:{scenario_id}:{mode}:{seed}".encode()).hexdigest()[:16]


def make_observation_pair(system_id: str, scenario_id: str, true_state: dict[str, bool], seed: int,
                          reachability: dict[str, bool] | None = None) -> dict[str, Any]:
    """Create linked complete and incomplete observations sharing identical true state."""
    keys = sorted(true_state)
    rng = np.random.default_rng(seed)
    hide_count = max(1, len(keys) // 4)
    hidden = sorted(rng.choice(keys, size=hide_count, replace=False).tolist())
    remaining = [key for key in keys if key not in hidden]
    delay_count = max(1, len(keys) // 8) if remaining else 0
    delayed = sorted(rng.choice(remaining, size=min(delay_count, len(remaining)), replace=False).tolist()) if remaining else []
    complete_id = _observation_id(system_id, scenario_id, "complete", seed)
    incomplete_id = _observation_id(system_id, scenario_id, "incomplete", seed)
    equivalence = hashlib.sha256("|".join(sorted(set(hidden + delayed))).encode()).hexdigest()[:12]
    reachability = reachability or {}
    complete = ObservationRecord(
        stage=0, observed_component_status=dict(true_state), unknown_component_status=[], delayed_component_status=[],
        communication_reachability=reachability, measurement_availability={k: True for k in keys},
        observation_id=complete_id, observation_equivalence_identifier=f"truth_{scenario_id}",
    )
    observed = {key: value for key, value in true_state.items() if key not in hidden and key not in delayed}
    incomplete = ObservationRecord(
        stage=0, observed_component_status=observed, unknown_component_status=hidden, delayed_component_status=delayed,
        communication_reachability=reachability, measurement_availability={k: k not in hidden for k in keys},
        observation_id=incomplete_id, observation_equivalence_identifier=equivalence,
    )
    return {
        "pair_id": f"pair_{scenario_id}", "system_id": system_id, "scenario_id": scenario_id,
        "true_state": dict(true_state), "complete": complete.model_dump(mode="json"),
        "incomplete": incomplete.model_dump(mode="json"), "unknown_set": hidden, "delayed_set": delayed,
        "observation_equivalence_identifier": equivalence,
    }


def observation_equivalent_example(system_id: str, seed: int) -> dict[str, Any]:
    """Create two distinct truths intentionally mapped to one incomplete observation."""
    truth_a = {"asset_visible": True, "asset_hidden": True}
    truth_b = {"asset_visible": True, "asset_hidden": False}
    observed = {"asset_visible": True}
    eq = hashlib.sha256(f"{system_id}:{seed}:equivalent".encode()).hexdigest()[:12]
    return {"system_id": system_id, "truth_a": truth_a, "truth_b": truth_b, "shared_incomplete_observation": observed,
            "unknown_set": ["asset_hidden"], "observation_equivalence_identifier": eq}

