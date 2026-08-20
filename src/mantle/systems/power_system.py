"""Traceable test-system loading, extraction, and AC power-flow validation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import math

import numpy as np
import pandas as pd
import pandapower as pp


def _finite(value: Any, default: float = 0.0) -> float:
    """Return a finite float for schema-safe serialization."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def load_network(root: str | Path, system_id: str) -> Any:
    """Load one standard network from its frozen source."""
    if system_id == "ieee14":
        return pp.from_json(Path(root) / "data" / "original" / "ieee14" / "case14.json")
    if system_id == "ieee39":
        return pp.from_json(Path(root) / "data" / "original" / "ieee39" / "case39.json")
    if system_id == "rts_gmlc":
        return pp.from_json(Path(root) / "data" / "original" / "rts_gmlc" / "pandapower_net.json")
    raise ValueError(f"unsupported system_id: {system_id}")


def _bus_external_id(net: Any, index: int) -> str:
    """Return official bus ID when present, otherwise deterministic zero-based index."""
    if "id" in net.bus.columns and pd.notna(net.bus.at[index, "id"]):
        return str(int(net.bus.at[index, "id"]))
    return str(int(index))


def extract_power_components(root: str | Path, system_id: str, net: Any) -> dict[str, Any]:
    """Extract typed-schema-compatible components without changing the source topology."""
    critical_ids = set()
    buses: list[dict[str, Any]] = []
    for idx, row in net.bus.iterrows():
        loads = net.load[(net.load.bus == idx) & net.load.in_service]
        coords = None
        if "geo" in row and isinstance(row.get("geo"), str):
            import json
            try:
                raw = json.loads(row["geo"])["coordinates"]
                coords = [float(raw[0]), float(raw[1])]
            except (ValueError, KeyError, TypeError):
                coords = None
        buses.append({
            "bus_id": _bus_external_id(net, idx), "base_kv": _finite(row.vn_kv, 1.0),
            "bus_type": str(row.get("type", "b")), "load_p": _finite(loads.p_mw.sum()),
            "load_q": _finite(loads.q_mvar.sum()), "critical_load_flag": False,
            "coordinates": coords,
        })
    branches: list[dict[str, Any]] = []
    branch_ids_seen: set[str] = set()
    for idx, row in net.line.iterrows():
        length = max(_finite(row.length_km, 1.0), 1e-9)
        limit = max(math.sqrt(3) * _finite(net.bus.at[int(row.from_bus), "vn_kv"], 1.0) * _finite(row.max_i_ka, 1.0), 1e-6)
        base_branch_id = f"branch_{row.get('name') if pd.notna(row.get('name')) else idx}"
        branch_id = base_branch_id if base_branch_id not in branch_ids_seen else f"{base_branch_id}_{idx}"
        branch_ids_seen.add(branch_id)
        branches.append({
            "branch_id": branch_id,
            "from_bus": _bus_external_id(net, int(row.from_bus)), "to_bus": _bus_external_id(net, int(row.to_bus)),
            "reactance": _finite(row.x_ohm_per_km) * length, "resistance": _finite(row.r_ohm_per_km) * length,
            "thermal_limit": limit, "initial_status": bool(row.in_service), "available": bool(row.in_service),
            "activated": bool(row.in_service), "repair_time": 4.0, "repair_cost": 1.0, "attack_cost": 1,
            "substation_id": None,
        })
    offset = len(branches)
    for idx, row in net.trafo.iterrows():
        base_branch_id = f"branch_trafo_{row.get('name') if pd.notna(row.get('name')) else idx}"
        branch_id = base_branch_id if base_branch_id not in branch_ids_seen else f"{base_branch_id}_{idx}"
        branch_ids_seen.add(branch_id)
        branches.append({
            "branch_id": branch_id,
            "from_bus": _bus_external_id(net, int(row.hv_bus)), "to_bus": _bus_external_id(net, int(row.lv_bus)),
            "reactance": _finite(row.vk_percent) / 100, "resistance": _finite(row.vkr_percent) / 100,
            "thermal_limit": max(_finite(row.sn_mva, 1.0), 1e-6), "initial_status": bool(row.in_service),
            "available": bool(row.in_service), "activated": bool(row.in_service), "repair_time": 6.0,
            "repair_cost": 1.5, "attack_cost": 1, "substation_id": f"transformer_{idx + offset}",
        })
    generators: list[dict[str, Any]] = []
    if system_id == "rts_gmlc":
        gen_csv = pd.read_csv(Path(root) / "data" / "original" / "rts_gmlc" / "gen.csv")
        for _, row in gen_csv.iterrows():
            fuel = str(row["Fuel"])
            generators.append({
                "generator_id": str(row["GEN UID"]), "bus_id": str(int(row["Bus ID"])),
                "p_min": _finite(row["PMin MW"]), "p_max": _finite(row["PMax MW"]),
                "ramp_up": max(_finite(row["Ramp Rate MW/Min"]) * 60, 0.0),
                "ramp_down": max(_finite(row["Ramp Rate MW/Min"]) * 60, 0.0),
                "black_start_capable": str(row["GEN UID"]) in {"113_STEAM_1", "213_STEAM_1", "313_STEAM_1"},
                "renewable": fuel in {"Wind", "Solar", "Hydro"}, "fuel": fuel,
                "initial_status": bool(_finite(row["MW Inj"]) > 0 or fuel not in {"Wind", "Solar", "Storage"}),
                "repair_time": max(_finite(row["MTTR Hr"], 8.0), 0.0), "attack_cost": 1,
            })
    else:
        for idx, row in net.gen.iterrows():
            generators.append({
                "generator_id": f"gen_{idx}", "bus_id": _bus_external_id(net, int(row.bus)),
                "p_min": _finite(row.min_p_mw), "p_max": _finite(row.max_p_mw),
                "ramp_up": max(_finite(row.max_p_mw), 1.0), "ramp_down": max(_finite(row.max_p_mw), 1.0),
                "black_start_capable": idx == 0 or (system_id == "ieee39" and idx == 4),
                "renewable": False, "fuel": "unspecified_standard_case", "initial_status": bool(row.in_service),
                "repair_time": 8.0, "attack_cost": 1,
            })
        for idx, row in net.ext_grid.iterrows():
            generators.append({
                "generator_id": f"slack_{idx}", "bus_id": _bus_external_id(net, int(row.bus)),
                "p_min": _finite(row.get("min_p_mw"), -1e6), "p_max": _finite(row.get("max_p_mw"), 1e6),
                "ramp_up": 1e6, "ramp_down": 1e6, "black_start_capable": True,
                "renewable": False, "fuel": "slack_equivalent", "initial_status": bool(row.in_service),
                "repair_time": 8.0, "attack_cost": 1,
            })
    storage: list[dict[str, Any]] = []
    if system_id == "rts_gmlc":
        store = pd.read_csv(Path(root) / "data" / "original" / "rts_gmlc" / "storage.csv")
        gen_source = pd.read_csv(Path(root) / "data" / "original" / "rts_gmlc" / "gen.csv").set_index("GEN UID")
        for _, row in store.iterrows():
            uid = str(row["GEN UID"])
            if uid not in gen_source.index or "STORAGE" not in uid:
                continue
            g = gen_source.loc[uid]
            storage.append({
                "storage_id": uid, "bus_id": str(int(g["Bus ID"])),
                "energy_capacity": max(_finite(row["Max Volume GWh"]) * 1000, 1.0),
                "power_charge_max": max(_finite(row["Rating MVA"]), 1.0),
                "power_discharge_max": max(_finite(row["Rating MVA"]), 1.0),
                "soc_initial": 0.5, "soc_min": 0.1, "soc_max": 0.9,
                "charge_efficiency": 0.92, "discharge_efficiency": 0.92, "mobile_flag": False,
            })
    return {"buses": buses, "branches": branches, "generators": generators, "storage": storage}


def select_rts_windows(root: str | Path) -> list[dict[str, Any]]:
    """Select reproducible low-load, peak-load, and renewable-ramp hours from official day-ahead data."""
    base = Path(root) / "data" / "original" / "rts_gmlc"
    load = pd.read_csv(base / "DAY_AHEAD_regional_Load.csv")
    wind = pd.read_csv(base / "DAY_AHEAD_wind.csv")
    pv = pd.read_csv(base / "DAY_AHEAD_pv.csv")
    load_total = load[["1", "2", "3"]].sum(axis=1)
    renewable = wind.iloc[:, 4:].sum(axis=1) + pv.iloc[:, 4:].sum(axis=1)
    variability = renewable.diff().abs().fillna(0)
    chosen = {
        "low_stress": int(load_total.idxmin()),
        "high_load": int(load_total.idxmax()),
        "high_renewable_variability": int(variability.idxmax()),
    }
    result: list[dict[str, Any]] = []
    for name, idx in chosen.items():
        stamp = load.loc[idx, ["Year", "Month", "Day", "Period"]].astype(int).to_dict()
        result.append({
            "name": name, "row_index": idx, "timestamp_fields": stamp,
            "regional_load_mw": {area: float(load.at[idx, area]) for area in ["1", "2", "3"]},
            "total_load_mw": float(load_total.at[idx]), "wind_mw": float(wind.iloc[idx, 4:].sum()),
            "pv_mw": float(pv.iloc[idx, 4:].sum()), "renewable_ramp_mw": float(variability.at[idx]),
        })
    return result


def _apply_rts_window(root: Path, net: Any, window: dict[str, Any]) -> None:
    """Apply official regional demand and utility PV/wind profiles to the official pandapower case."""
    # Regional load scaling preserves the official bus-level spatial distribution.
    for area in [1, 2, 3]:
        buses = net.bus.index[net.bus.zone.astype(float).round().astype(int) == area]
        rows = net.load.index[net.load.bus.isin(buses)]
        base_total = float(net.load.loc[rows, "p_mw"].sum())
        scale = window["regional_load_mw"][str(area)] / base_total
        net.load.loc[rows, "scaling"] = scale

    source = pd.read_csv(root / "data" / "original" / "rts_gmlc" / "gen.csv")
    pv = pd.read_csv(root / "data" / "original" / "rts_gmlc" / "DAY_AHEAD_pv.csv")
    wind = pd.read_csv(root / "data" / "original" / "rts_gmlc" / "DAY_AHEAD_wind.csv")
    profile = {col: float(pv.at[window["row_index"], col]) for col in pv.columns[4:]}
    profile.update({col: float(wind.at[window["row_index"], col]) for col in wind.columns[4:]})
    bus_ids = net.bus.id.astype(int)
    used: set[int] = set()
    special = source[source["Fuel"].isin(["Wind", "Solar", "Storage", "Sync_Cond"])]
    for _, row in special.iterrows():
        uid = str(row["GEN UID"])
        bus = int(row["Bus ID"])
        pmax = float(row["PMax MW"])
        candidates = net.sgen.index[
            (net.sgen.bus.map(bus_ids).astype(int) == bus)
            & np.isclose(net.sgen.max_p_mw.astype(float), pmax, atol=1e-6)
            & (~net.sgen.index.isin(list(used)))
        ]
        if len(candidates) == 0:
            if pmax == 0:
                continue
            raise ValueError(f"cannot map RTS renewable/storage element {uid} to official pandapower element")
        element = int(candidates[0])
        used.add(element)
        p_mw = profile.get(uid, 0.0)
        net.sgen.at[element, "p_mw"] = min(max(float(p_mw), 0.0), pmax)
        net.sgen.at[element, "q_mvar"] = 0.0
        net.sgen.at[element, "in_service"] = uid in profile
    net._mantle_excluded_sgen_indices = used


def _pre_dispatch_rts(net: Any) -> None:
    """Construct a deterministic feasible commitment/dispatch before AC validation.

    This is a validation dispatch, not restoration optimization. Units are committed by
    descending capacity and dispatched within declared Pmin/Pmax bounds.
    """
    excluded = set(getattr(net, "_mantle_excluded_sgen_indices", set()))
    ext_min = _finite(net.ext_grid.min_p_mw.iloc[0], 0.0)
    ext_max = _finite(net.ext_grid.max_p_mw.iloc[0], 0.0)
    ext_target = (ext_min + ext_max) / 2
    bus_ids = net.bus.id.astype(int)
    units_by_area: dict[int, list[tuple[str, int, float, float]]] = {1: [], 2: [], 3: []}
    for table in ["gen", "sgen"]:
        df = getattr(net, table)
        for idx, row in df.iterrows():
            if table == "sgen" and int(idx) in excluded:
                continue
            pmin = max(_finite(row.get("min_p_mw"), 0.0), 0.0)
            pmax = max(_finite(row.get("max_p_mw"), 0.0), 0.0)
            if pmax > 0:
                area = int(bus_ids.at[int(row.bus)]) // 100
                units_by_area[area].append((table, int(idx), pmin, pmax))
                getattr(net, table).at[idx, "in_service"] = False
            elif table == "gen":
                # Preserve synchronous condensers for intact-state voltage support.
                getattr(net, table).at[idx, "p_mw"] = 0.0
                getattr(net, table).at[idx, "in_service"] = True
            else:
                getattr(net, table).at[idx, "in_service"] = False
    curtailment = 0.0
    for area in [1, 2, 3]:
        area_buses = net.bus.index[(bus_ids // 100) == area]
        load_rows = net.load.index[net.load.bus.isin(area_buses)]
        demand = float((net.load.loc[load_rows, "p_mw"] * net.load.loc[load_rows, "scaling"]).sum())
        renewable_rows = [idx for idx in excluded if idx in net.sgen.index and int(net.sgen.at[idx, "bus"]) in area_buses]
        renewable = float(net.sgen.loc[renewable_rows, "p_mw"].sum()) if renewable_rows else 0.0
        units = sorted(units_by_area[area], key=lambda item: (-item[3], item[0], item[1]))
        mandatory_units = [u for u in units if u[0] == "gen" and u[3] > 0]
        area_ext = ext_target if area == 1 else 0.0
        mandatory_min = sum(u[2] for u in mandatory_units)
        allowed_renewable = max(0.0, demand * 1.02 - area_ext - mandatory_min)
        if renewable > allowed_renewable and renewable > 0:
            scale = allowed_renewable / renewable
            net.sgen.loc[renewable_rows, "p_mw"] *= scale
            curtailment += renewable - allowed_renewable
            renewable = allowed_renewable
        target = max(mandatory_min, demand * 1.02 - renewable - area_ext)
        committed: list[tuple[str, int, float, float]] = list(mandatory_units)
        min_sum = sum(u[2] for u in mandatory_units)
        max_sum = sum(u[3] for u in mandatory_units)
        for unit in units:
            if unit in mandatory_units or max_sum >= target:
                continue
            if min_sum + unit[2] <= target + 1e-9:
                committed.append(unit)
                min_sum += unit[2]
                max_sum += unit[3]
        if max_sum + 1e-6 < target:
            raise ValueError(f"RTS area {area} validation dispatch lacks capacity: target={target:.3f}, max={max_sum:.3f}")
        remaining = target - min_sum
        headroom = max_sum - min_sum
        for table, idx, pmin, pmax in committed:
            dispatch = pmin + (remaining * (pmax - pmin) / headroom if headroom > 0 else 0.0)
            getattr(net, table).at[idx, "p_mw"] = dispatch
            getattr(net, table).at[idx, "in_service"] = True
    net._mantle_renewable_curtailment_mw = curtailment


def _rebalance_slack(net: Any, max_iterations: int = 5) -> None:
    """Move active generation within declared bounds so the slack remains within limits."""
    for _ in range(max_iterations):
        pp.runpp(net, algorithm="nr", calculate_voltage_angles=True, init="auto", max_iteration=50, tolerance_mva=1e-8)
        if len(net.ext_grid) == 0:
            return
        p = float(net.res_ext_grid.p_mw.iloc[0])
        lo = _finite(net.ext_grid.min_p_mw.iloc[0], -1e9)
        hi = _finite(net.ext_grid.max_p_mw.iloc[0], 1e9)
        if lo - 1e-6 <= p <= hi + 1e-6:
            return
        desired = (lo + hi) / 2
        delta = p - desired
        frames: list[tuple[str, int, float]] = []
        for table in ["gen", "sgen"]:
            df = getattr(net, table)
            for idx, row in df[df.in_service].iterrows():
                current = float(row.p_mw)
                lower = _finite(row.get("min_p_mw"), current)
                upper = _finite(row.get("max_p_mw"), current)
                room = (upper - current) if delta > 0 else (current - lower)
                if room > 1e-8 and not (current == 0 and lower == 0):
                    frames.append((table, int(idx), room))
        capacity = sum(item[2] for item in frames)
        if capacity + 1e-9 < abs(delta):
            return
        for table, idx, room in frames:
            step = abs(delta) * room / capacity
            getattr(net, table).at[idx, "p_mw"] += step if delta > 0 else -step


def validate_power_flow(root: str | Path, system_id: str, window: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run an actual AC Newton-Raphson flow and report convergence, limits, and balance."""
    root_path = Path(root)
    net = load_network(root_path, system_id)
    if system_id == "rts_gmlc" and window is not None:
        _apply_rts_window(root_path, net, window)
        _pre_dispatch_rts(net)
        _rebalance_slack(net)
    else:
        pp.runpp(net, algorithm="nr", calculate_voltage_angles=True, init="auto", max_iteration=50, tolerance_mva=1e-8)
        _rebalance_slack(net)
    line_violations = int((net.res_line.loading_percent > net.line.max_loading_percent).sum()) if len(net.line) else 0
    trafo_violations = int((net.res_trafo.loading_percent > net.trafo.max_loading_percent).sum()) if len(net.trafo) else 0
    gen_violations = 0
    if len(net.gen):
        active = net.gen.in_service.astype(bool)
        gen_violations += int((((net.res_gen.p_mw < net.gen.min_p_mw - 1e-6) | (net.res_gen.p_mw > net.gen.max_p_mw + 1e-6)) & active).sum())
    if len(net.sgen):
        active_sgen = net.sgen.in_service.astype(bool)
        gen_violations += int((((net.res_sgen.p_mw < net.sgen.min_p_mw - 1e-6) | (net.res_sgen.p_mw > net.sgen.max_p_mw + 1e-6)) & active_sgen).sum())
    if len(net.ext_grid):
        ext = net.res_ext_grid.p_mw
        gen_violations += int(((ext < net.ext_grid.min_p_mw - 1e-6) | (ext > net.ext_grid.max_p_mw + 1e-6)).sum())
    losses = float(net.res_line.pl_mw.sum()) + (float(net.res_trafo.pl_mw.sum()) if len(net.trafo) else 0.0)
    balance_residual = abs(float(net.res_bus.p_mw.sum()) + losses)
    return {
        "system_id": system_id, "window": None if window is None else window["name"],
        "converged": bool(net.converged), "balance_residual_mw": balance_residual,
        "line_limit_violations": line_violations, "transformer_limit_violations": trafo_violations,
        "generator_limit_violations": gen_violations, "max_line_loading_percent": _finite(net.res_line.loading_percent.max()),
        "max_transformer_loading_percent": _finite(net.res_trafo.loading_percent.max()) if len(net.trafo) else 0.0,
        "min_voltage_pu": _finite(net.res_bus.vm_pu.min()), "max_voltage_pu": _finite(net.res_bus.vm_pu.max()),
        "network_loss_mw": losses,
        "renewable_curtailment_mw": _finite(getattr(net, "_mantle_renewable_curtailment_mw", 0.0)),
    }
