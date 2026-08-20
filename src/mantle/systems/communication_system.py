"""Deterministic communication/control overlay generation and reachability."""

from __future__ import annotations

from typing import Any
import networkx as nx

from mantle.schemas.communication import CommunicationLink, CommunicationNode


def build_communication_variants(config: dict[str, Any], remote_assets: list[str]) -> dict[str, Any]:
    """Build fixed tree, meshed, and redundant-meshed variants with canonical endpoints."""
    system_id = config["system_id"]
    main = f"{system_id}_MAIN"
    regional = [f"{system_id}_REG_{bus}" for bus in config["regional_control_buses"]]
    field = [f"{system_id}_FIELD_{bus}" for bus in config["field_buses"]]
    nodes: list[CommunicationNode] = [CommunicationNode(
        comm_node_id=main, node_type="main_control_centre", mapped_power_assets=[],
        power_supply_bus=str(config["main_control_bus"]), backup_power_duration=config["backup_power_hours"]["main"],
        remote_control_capability=True, measurement_capability=True, local_autonomy_capability=True,
        canonical_control_endpoint=main, repair_time=6, attack_cost=1, emergency_attachment_point=True,
    )]
    for idx, node in enumerate(regional):
        nodes.append(CommunicationNode(
            comm_node_id=node, node_type="regional_control_centre", mapped_power_assets=[],
            power_supply_bus=str(config["regional_control_buses"][idx]), backup_power_duration=config["backup_power_hours"]["regional"],
            remote_control_capability=True, measurement_capability=True, local_autonomy_capability=idx == 0,
            canonical_control_endpoint=node, repair_time=5, attack_cost=1, emergency_attachment_point=True,
        ))
    for idx, node in enumerate(field):
        nodes.append(CommunicationNode(
            comm_node_id=node, node_type="field_communication_node", mapped_power_assets=[],
            power_supply_bus=str(config["field_buses"][idx]), backup_power_duration=config["backup_power_hours"]["field"],
            remote_control_capability=True, measurement_capability=True,
            local_autonomy_capability=(idx / max(len(field), 1)) < float(config["local_autonomy_ratio"]),
            canonical_control_endpoint=node, repair_time=4, attack_cost=1, emergency_attachment_point=idx < 2,
        ))
    endpoints: dict[str, str] = {}
    for idx, asset in enumerate(remote_assets):
        endpoint = f"{system_id}_DEV_{asset}"
        supply = str(config["field_buses"][idx % len(config["field_buses"])]) if config["field_buses"] else str(config["main_control_bus"])
        local = (idx / max(len(remote_assets), 1)) < float(config["local_autonomy_ratio"])
        nodes.append(CommunicationNode(
            comm_node_id=endpoint, node_type="device_terminal", mapped_power_assets=[asset], power_supply_bus=supply,
            backup_power_duration=config["backup_power_hours"]["device"], remote_control_capability=True,
            measurement_capability=True, local_autonomy_capability=local, canonical_control_endpoint=endpoint,
            repair_time=2, attack_cost=1, emergency_attachment_point=False,
        ))
        endpoints[asset] = endpoint

    def link(a: str, b: str, idx: int, redundant: bool = False) -> CommunicationLink:
        """Create one deterministic communication edge."""
        return CommunicationLink(
            comm_link_id=f"{system_id}_CL_{idx:03d}", from_node=a, to_node=b,
            link_type="backup" if redundant else "primary", capacity=100.0, latency=5.0,
            repair_time=float(config["link_repair_time_hours"]), attack_cost=1, redundant_flag=redundant,
        )

    tree: list[CommunicationLink] = []
    counter = 0
    for reg in regional:
        tree.append(link(main, reg, counter)); counter += 1
    for idx, fld in enumerate(field):
        parent = regional[idx % len(regional)] if regional else main
        tree.append(link(parent, fld, counter)); counter += 1
    device_nodes = [endpoints[a] for a in remote_assets]
    for idx, device in enumerate(device_nodes):
        parent = field[idx % len(field)] if field else (regional[idx % len(regional)] if regional else main)
        tree.append(link(parent, device, counter)); counter += 1
    meshed = list(tree)
    if len(regional) > 1:
        for idx in range(len(regional)):
            meshed.append(link(regional[idx], regional[(idx + 1) % len(regional)], counter, True)); counter += 1
    if len(field) > 2:
        stride = max(2, len(field) // max(len(regional), 1))
        for idx in range(0, len(field), stride):
            meshed.append(link(field[idx], field[(idx + stride) % len(field)], counter, True)); counter += 1
    redundant_mesh = list(meshed)
    for idx, fld in enumerate(field):
        redundant_mesh.append(link(main if idx % 2 == 0 else regional[idx % len(regional)], fld, counter, True)); counter += 1
    return {
        "nodes": [item.model_dump(mode="json") for item in nodes],
        "variants": {
            "tree": [item.model_dump(mode="json") for item in tree],
            "meshed": [item.model_dump(mode="json") for item in meshed],
            "redundant_meshed": [item.model_dump(mode="json") for item in redundant_mesh],
        },
        "default_topology": "meshed", "main_control_node": main, "canonical_endpoints": endpoints,
    }


def communication_graph(communication: dict[str, Any], variant: str = "meshed", failed_links: set[str] | None = None,
                        failed_nodes: set[str] | None = None) -> nx.Graph:
    """Materialize a topology after link/node failures."""
    failed_links = failed_links or set()
    failed_nodes = failed_nodes or set()
    graph = nx.Graph()
    for node in communication["nodes"]:
        if node["initial_status"] and node["comm_node_id"] not in failed_nodes:
            graph.add_node(node["comm_node_id"])
    for edge in communication["variants"][variant]:
        if edge["initial_status"] and edge["comm_link_id"] not in failed_links:
            if edge["from_node"] in graph and edge["to_node"] in graph:
                graph.add_edge(edge["from_node"], edge["to_node"], **edge)
    return graph


def reachable_endpoints(communication: dict[str, Any], variant: str = "meshed", failed_links: set[str] | None = None,
                        failed_nodes: set[str] | None = None) -> set[str]:
    """Return endpoints reachable from the main control centre."""
    graph = communication_graph(communication, variant, failed_links, failed_nodes)
    main = communication["main_control_node"]
    return set(nx.node_connected_component(graph, main)) if main in graph else set()


def node_powered(node: dict[str, Any], supply_available: bool, elapsed_hours: float) -> bool:
    """Apply the communication-node electrical dependency and backup duration."""
    return bool(node["initial_status"] and (supply_available or elapsed_hours < float(node["backup_power_duration"])))


def locally_controllable(node: dict[str, Any], remotely_reachable: bool) -> bool:
    """Retain local controllability when remote communication is lost."""
    return bool(remotely_reachable or node["local_autonomy_capability"])
