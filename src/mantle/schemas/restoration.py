"""Restoration-resource schemas."""

from pydantic import BaseModel, ConfigDict, Field


class RepairCrew(BaseModel):
    """A crew that may occupy at most one repair task."""

    model_config = ConfigDict(extra="forbid")
    crew_id: str
    initial_location: str
    current_location: str
    travel_speed: float = Field(gt=0)
    eligible_asset_types: list[str]
    repair_capacity: int = Field(ge=1)
    occupied_asset: str | None = None
    remaining_repair_time: float = Field(default=0, ge=0)


class EmergencyCommunicationUnit(BaseModel):
    """Deployable communication restoration unit."""

    model_config = ConfigDict(extra="forbid")
    unit_id: str
    initial_location: str
    current_location: str
    deployment_time: float = Field(ge=0)
    supported_nodes: list[str]
    operating_duration: float = Field(gt=0)
    available: bool = True
    deployed_node: str | None = None


class MobileStorageUnit(BaseModel):
    """Mobile storage with a unique connection location."""

    model_config = ConfigDict(extra="forbid")
    unit_id: str
    initial_bus: str
    current_bus: str
    energy_capacity: float = Field(gt=0)
    power_capacity: float = Field(gt=0)
    travel_time_matrix: dict[str, float]
    connected: bool = False


class BlackStartResource(BaseModel):
    """Black-start resource with startup delay and availability."""

    model_config = ConfigDict(extra="forbid")
    resource_id: str
    generator_id: str
    startup_time: float = Field(ge=0)
    startup_energy: float = Field(ge=0)
    initial_availability: bool = True

