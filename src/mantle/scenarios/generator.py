"""Configuration- and seed-controlled legal scenario-library generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mantle.schemas.disruption import DisruptionAction, Scenario
from mantle.scenarios.observations import make_observation_pair, observation_equivalent_example
from mantle.utilities.config import load_yaml
from mantle.utilities.reproducibility import SeedManager
from mantle.utilities.serialization import write_json


def _targets(system: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Return exposed power, communication, and observation targets."""
    power = list(system["metadata"]["candidate_disrupted_components"])
    comm = [edge["comm_link_id"] for edge in system["communication"]["variants"]["meshed"]]
    observation = [node["comm_node_id"] for node in system["communication"]["nodes"] if node["measurement_capability"]]
    return power, comm, observation


def _make_actions(family: str, budget: int, secondary_stage: int, power: list[str], comm: list[str], observation: list[str],
                  rng: Any, scenario_id: str) -> list[DisruptionAction]:
    """Create a legal non-repeating action sequence for one scenario family."""
    pools = {
        "I": [("power", "physical_asset", power, "physical_outage")],
        "II": [("power", "physical_asset", power, "physical_outage"), ("communication", "communication_link", comm, "communication_outage")],
        "III": [("power", "physical_asset", power, "physical_outage"), ("observation", "measurement_path", observation, "observation_loss")],
        "IV": [("power", "physical_asset", power, "physical_outage"), ("communication", "communication_link", comm, "communication_outage")],
        "V": [("power", "physical_asset", power, "physical_outage"), ("communication", "communication_link", comm, "communication_outage"), ("observation", "measurement_path", observation, "delayed_report")],
    }[family]
    actions: list[DisruptionAction] = []
    used: set[str] = set()
    for idx in range(budget):
        layer, target_type, choices, effect = pools[idx % len(pools)]
        available = [item for item in choices if item not in used]
        if not available:
            continue
        target = str(available[int(rng.integers(0, len(available)))])
        used.add(target)
        secondary = family in {"IV", "V"} and idx == budget - 1
        stage = secondary_stage if secondary else 0
        actions.append(DisruptionAction(
            action_id=f"{scenario_id}_A{idx+1}", stage=stage, layer=layer, target_type=target_type,
            target_id=target, abstract_cost=1, effect_type=effect, effect_duration=2,
            observation_visibility="hidden" if layer == "observation" or family in {"III", "V"} else "reported",
            secondary_disruption_flag=secondary,
        ))
    return actions


def validate_scenario(scenario: dict[str, Any], existing_targets: set[str], exposed_targets: set[str]) -> None:
    """Apply Phase 1 scenario legality constraints."""
    seen: set[str] = set()
    for action in scenario["action_list"]:
        if action["target_id"] not in existing_targets:
            raise ValueError("action target does not exist")
        if action["target_id"] in seen:
            raise ValueError("illegal repeated disruption target")
        seen.add(action["target_id"])
        if action["layer"] == "power" and action["target_id"] not in exposed_targets:
            raise ValueError("remote disruption target is not exposed")
        if action["effect_duration"] <= 0:
            raise ValueError("effect duration must be positive")
        if action["secondary_disruption_flag"] and action["stage"] != scenario["secondary_disruption_stage"]:
            raise ValueError("secondary disruption occurs at an invalid stage")
    if scenario["total_abstract_cost"] > scenario["budget"]:
        raise ValueError("abstract budget exceeded")


def generate_library(root: str | Path) -> dict[str, Any]:
    """Generate all systems/families and linked incomplete-observation pairs."""
    root_path = Path(root)
    sets = load_yaml(root_path / "configs" / "disruptions" / "scenario_sets.yaml")
    templates = load_yaml(root_path / "configs" / "disruptions" / "scenario_templates.yaml")
    global_config = load_yaml(root_path / "configs" / "global.yaml")
    seed_manager = SeedManager(int(global_config["random_seed"]))
    output = root_path / "results" / "phase1" / "scenario_summaries"
    scenario_dir = output / "library"
    observation_dir = output / "observation_pairs"
    scenarios: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    stats: dict[str, dict[str, int]] = {}
    for system_id in ["ieee14", "ieee39", "rts_gmlc"]:
        from mantle.utilities.serialization import read_json
        system = read_json(root_path / "data" / "modified" / system_id / "coupled_system.json")
        power, comm, observation = _targets(system)
        existing = set(power + comm + observation)
        stats[system_id] = {}
        for family in templates["families"]:
            stats[system_id][family] = 0
            for idx in range(int(sets["scenario_count_per_family_per_system"])):
                budget = idx % int(sets["B_max"]) + 1
                namespace = f"scenario:{system_id}:{family}:{idx}"
                child_seed = seed_manager.child_seed(namespace)
                rng = seed_manager.rng(namespace)
                scenario_id = f"{system_id}_{family}_{idx+1:03d}"
                actions = _make_actions(family, budget, int(sets["secondary_disruption_stage"]), power, comm, observation, rng, scenario_id)
                secondary = int(sets["secondary_disruption_stage"]) if family in {"IV", "V"} else None
                scenario = Scenario(
                    scenario_id=scenario_id, system_id=system_id, family=family, seed=child_seed,
                    horizon=int(sets["horizon"]), budget=budget, initial_disruption_stage=0,
                    secondary_disruption_stage=secondary, action_list=actions,
                    total_abstract_cost=sum(a.abstract_cost for a in actions),
                    observation_mode=templates["families"][family]["observation_mode"],
                    restoration_resource_configuration=f"configs/restoration/{system_id}_resources.yaml",
                    metadata={"abstract_budget_not_weapon_count": True, "event_order": "configs/global.yaml", "policy": "no_action_validation"},
                ).model_dump(mode="json")
                validate_scenario(scenario, existing, set(power))
                write_json(scenario_dir / system_id / f"{scenario_id}.json", scenario)
                scenarios.append(scenario)
                stats[system_id][family] += 1
                if scenario["observation_mode"] == "incomplete":
                    true_state = {target: True for target in sorted(existing)[:max(8, min(30, len(existing)))]}
                    for action in scenario["action_list"]:
                        if action["target_id"] in true_state:
                            true_state[action["target_id"]] = False
                    pair = make_observation_pair(system_id, scenario_id, true_state, seed_manager.child_seed(f"observation:{scenario_id}"))
                    write_json(observation_dir / system_id / f"{scenario_id}_pair.json", pair)
                    pairs.append(pair)
        equivalent = observation_equivalent_example(system_id, seed_manager.child_seed(f"equivalence:{system_id}"))
        write_json(observation_dir / system_id / "observation_equivalent_example.json", equivalent)
    summary = {"scenario_count": len(scenarios), "observation_pair_count": len(pairs), "statistics": stats,
               "event_order": global_config["event_order"], "B_interpretation": "abstract disruption-resource budget"}
    write_json(output / "scenario_library_summary.json", summary)
    write_json(output / "scenario_library.json", scenarios)
    return summary
