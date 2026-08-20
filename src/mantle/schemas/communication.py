"""Communication and control overlay schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CommunicationNode(BaseModel):
    """A powered communication/control node with explicit dependencies."""

    model_config = ConfigDict(extra="forbid")
    comm_node_id: str
    node_type: str
    mapped_power_assets: list[str]
    power_supply_bus: str
    backup_power_duration: float = Field(ge=0)
    remote_control_capability: bool
    measurement_capability: bool
    local_autonomy_capability: bool
    canonical_control_endpoint: str
    initial_status: bool = True
    repair_time: float = Field(ge=0)
    attack_cost: int = Field(ge=1)
    emergency_attachment_point: bool = False


class CommunicationLink(BaseModel):
    """Communication link, including backup/redundancy status."""

    model_config = ConfigDict(extra="forbid")
    comm_link_id: str
    from_node: str
    to_node: str
    link_type: str
    capacity: float = Field(gt=0)
    latency: float = Field(ge=0)
    initial_status: bool = True
    repair_time: float = Field(ge=0)
    attack_cost: int = Field(ge=1)
    redundant_flag: bool = False

