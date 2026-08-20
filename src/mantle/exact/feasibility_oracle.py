"""Deterministic DC load-shedding feasibility oracle shared by both solvers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

from .actions import RestorationAction
from .state import COMPONENTS, ExactState, MISSION_IDS


ROOT = Path(__file__).resolve().parents[3]
SYSTEM_PATH = ROOT / "data" / "modified" / "ieee14" / "coupled_system.json"
MISSION_PATH = ROOT / "data" / "modified" / "ieee14" / "mission_mapping.json"


@dataclass(frozen=True)
class OracleResult:
    """Canonical solution and all quantities consumed by the exact game."""

    feasible: bool
    served_bus_loads: tuple[tuple[str, float], ...]
    mission_inputs: tuple[tuple[str, float, bool], ...]
    generator_dispatch: tuple[tuple[str, float], ...]
    line_flows: tuple[tuple[str, float], ...]
    resource_successor: tuple[Any, ...]
    activation_successor: tuple[int, ...]
    objective_components: tuple[float, float, float, float]
    solver_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation."""

        return asdict(self)


@lru_cache(maxsize=1)
def _model_data() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with SYSTEM_PATH.open("r", encoding="utf-8") as handle:
        system = json.load(handle)
    with MISSION_PATH.open("r", encoding="utf-8") as handle:
        missions = json.load(handle)
    return system, missions


def _status_map(state: ExactState) -> dict[str, int]:
    return {
        component: int(state.availability[index] and state.activation[index])
        for index, component in enumerate(COMPONENTS)
    }


@lru_cache(maxsize=4096)
def _solve_cached(state: ExactState, switching_cost: float, resource_cost: float) -> OracleResult:
    system, missions = _model_data()
    power = system["power"]
    buses = sorted(power["buses"], key=lambda row: int(row["bus_id"]))
    generators = sorted(power["generators"], key=lambda row: row["generator_id"])
    branches = sorted(power["branches"], key=lambda row: row["branch_id"])
    bus_index = {row["bus_id"]: index for index, row in enumerate(buses)}
    g_count, b_count, l_count = len(generators), len(buses), len(branches)
    g0, s0, th0, f0 = 0, g_count, g_count + b_count, g_count + 2 * b_count
    variable_count = g_count + 2 * b_count + l_count
    loads = np.array([float(row.get("load_p", 0.0) or 0.0) for row in buses])
    status = _status_map(state)

    bounds: list[tuple[float | None, float | None]] = []
    for generator in generators:
        active = status.get(generator["generator_id"], 1)
        bounds.append((0.0, float(generator["p_max"]) * active))
    for index, row in enumerate(buses):
        upper = loads[index]
        if row["bus_id"] == "3":
            upper *= status["bus_3"]
        bounds.append((0.0, upper))
    for index in range(b_count):
        bounds.append((0.0, 0.0) if index == 0 else (-10.0, 10.0))
    for branch in branches:
        active = status.get(branch["branch_id"], 1)
        limit = float(branch["thermal_limit"]) if active else 0.0
        bounds.append((-limit, limit))

    equalities: list[np.ndarray] = []
    rhs: list[float] = []
    for bus_id, index in bus_index.items():
        row = np.zeros(variable_count)
        for generator_index, generator in enumerate(generators):
            if generator["bus_id"] == bus_id:
                row[g0 + generator_index] += 1.0
        row[s0 + index] -= 1.0
        for branch_index, branch in enumerate(branches):
            if branch["from_bus"] == bus_id:
                row[f0 + branch_index] -= 1.0
            if branch["to_bus"] == bus_id:
                row[f0 + branch_index] += 1.0
        equalities.append(row)
        rhs.append(0.0)
    for branch_index, branch in enumerate(branches):
        if status.get(branch["branch_id"], 1) == 0:
            continue
        row = np.zeros(variable_count)
        scale = 100.0 / max(abs(float(branch["reactance"])), 1.0e-6)
        row[f0 + branch_index] = 1.0
        row[th0 + bus_index[branch["from_bus"]]] = -scale
        row[th0 + bus_index[branch["to_bus"]]] = scale
        equalities.append(row)
        rhs.append(0.0)

    mission_objective = np.zeros(variable_count)
    for mission in missions:
        bus_id = mission["mapped_power_buses"][0]
        load = max(loads[bus_index[bus_id]], 1.0)
        mission_objective[s0 + bus_index[bus_id]] -= 1.0 / load
    first = linprog(
        mission_objective,
        A_eq=np.array(equalities),
        b_eq=np.array(rhs),
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    if not first.success:
        return OracleResult(False, (), (), (), (), (), state.activation, (), first.message)

    all_load_objective = np.zeros(variable_count)
    all_load_objective[s0 : s0 + b_count] = -1.0
    a_ub = np.array([mission_objective])
    b_ub = np.array([float(first.fun) + 1.0e-8])
    second = linprog(
        all_load_objective,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=np.array(equalities),
        b_eq=np.array(rhs),
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )
    solution = second.x if second.success else first.x
    served = tuple(
        (row["bus_id"], round(float(solution[s0 + index]), 8))
        for index, row in enumerate(buses)
    )
    served_map = dict(served)
    main_up = bool(status["ieee14_MAIN"] or state.resources.emergency_comm)
    field_up = bool(status["ieee14_FIELD_3"] or state.resources.emergency_comm)
    mission_inputs: list[tuple[str, float, bool]] = []
    for mission in missions:
        bus_id = mission["mapped_power_buses"][0]
        ratio = served_map[bus_id] / max(loads[bus_index[bus_id]], 1.0e-12)
        if not mission["communication_required"]:
            communication = True
        elif mission["mission_id"] == "ieee14_medical":
            communication = main_up and field_up
        else:
            communication = main_up
        mission_inputs.append((mission["mission_id"], round(ratio, 8), communication))
    mission_loss = round(sum(max(0.0, 1.0 - row[1]) for row in mission_inputs), 8)
    eens = round(float(loads.sum() - sum(value for _, value in served)), 8)
    return OracleResult(
        feasible=True,
        served_bus_loads=served,
        mission_inputs=tuple(mission_inputs),
        generator_dispatch=tuple(
            (row["generator_id"], round(float(solution[g0 + index]), 8))
            for index, row in enumerate(generators)
        ),
        line_flows=tuple(
            (row["branch_id"], round(float(solution[f0 + index]), 8))
            for index, row in enumerate(branches)
        ),
        resource_successor=(
            state.resources.crew_target,
            state.resources.repair_remaining,
            state.resources.emergency_comm,
            state.resources.local_autonomy,
        ),
        activation_successor=state.activation,
        objective_components=(mission_loss, eens, resource_cost, switching_cost),
        solver_status="optimal",
    )


def solve_stage_feasibility(
    state: ExactState, restoration_action: RestorationAction
) -> OracleResult:
    """Solve the frozen DC stage problem with deterministic canonical output."""

    switching_cost = 1.0 if restoration_action.kind in {"isolate", "activate", "repair_activate"} else 0.0
    resource_cost = 1.0 if restoration_action.kind in {
        "repair",
        "repair_activate",
        "deploy_emergency_comm",
        "enable_local_autonomy",
    } else 0.0
    return _solve_cached(state, switching_cost, resource_cost)


def oracle_cache_info() -> dict[str, int]:
    """Expose cache counters for transparent runtime accounting."""

    info = _solve_cached.cache_info()
    return {"hits": info.hits, "misses": info.misses, "size": info.currsize}


def clear_oracle_cache() -> None:
    """Clear only the allowed deterministic feasibility memoization cache."""

    _solve_cached.cache_clear()
