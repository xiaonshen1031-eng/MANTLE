"""Mission service definitions and finite-state runtime."""

from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class MissionState(StrEnum):
    """Required deterministic mission states."""

    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    BACKUP = "BACKUP"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"
    RESTORED = "RESTORED"


class Mission(BaseModel):
    """Configuration of a mission-critical service."""

    model_config = ConfigDict(extra="forbid")
    mission_id: str
    mission_name: str
    mission_type: str
    mapped_power_buses: list[str]
    mapped_communication_nodes: list[str]
    minimum_power_requirement: float = Field(gt=0, le=1)
    maximum_interruption_duration: int = Field(ge=0)
    minimum_recovery_duration: int = Field(ge=1)
    backup_energy_duration: int = Field(ge=0)
    dependency_type: str
    communication_required: bool
    priority_metadata: dict[str, int | str]
    initial_state: MissionState = MissionState.NORMAL
    failure_states: list[str] = ["insufficient_power", "communication_unavailable", "backup_expired"]


class MissionRuntime(BaseModel):
    """Mutable timers used by the mission finite-state machine."""

    model_config = ConfigDict(extra="forbid")
    state: MissionState = MissionState.NORMAL
    interruption_duration: int = Field(default=0, ge=0)
    backup_remaining: int = Field(default=0, ge=0)
    recovery_duration: int = Field(default=0, ge=0)

