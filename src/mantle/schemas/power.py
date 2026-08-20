"""Power-system component schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Forbid undocumented fields in experiment-critical artifacts."""

    model_config = ConfigDict(extra="forbid")


class PowerBus(StrictModel):
    """Electrical bus and attached demand."""

    bus_id: str
    base_kv: float = Field(gt=0)
    bus_type: str
    load_p: float = Field(ge=0)
    load_q: float
    critical_load_flag: bool = False
    coordinates: tuple[float, float] | None = None


class PowerBranch(StrictModel):
    """AC branch or transformer with availability and activation separated."""

    branch_id: str
    from_bus: str
    to_bus: str
    reactance: float
    resistance: float
    thermal_limit: float = Field(gt=0)
    initial_status: bool = True
    available: bool = True
    activated: bool = True
    repair_time: float = Field(ge=0)
    repair_cost: float = Field(ge=0)
    attack_cost: int = Field(ge=1)
    substation_id: str | None = None

    @model_validator(mode="after")
    def activation_requires_availability(self) -> "PowerBranch":
        """Enforce e_k,t <= v_k,t."""
        if self.activated and not self.available:
            raise ValueError("activated branch must be available")
        return self


class Generator(StrictModel):
    """Generation unit metadata required for restoration studies."""

    generator_id: str
    bus_id: str
    p_min: float
    p_max: float = Field(ge=0)
    ramp_up: float = Field(ge=0)
    ramp_down: float = Field(ge=0)
    black_start_capable: bool = False
    renewable: bool = False
    fuel: str = "unknown"
    initial_status: bool = True
    repair_time: float = Field(ge=0)
    attack_cost: int = Field(ge=1)

    @model_validator(mode="after")
    def valid_limits(self) -> "Generator":
        """Reject inverted active-power bounds."""
        if self.p_min > self.p_max:
            raise ValueError("p_min cannot exceed p_max")
        return self


class Storage(StrictModel):
    """Stationary or mobile electrical storage."""

    storage_id: str
    bus_id: str
    energy_capacity: float = Field(gt=0)
    power_charge_max: float = Field(gt=0)
    power_discharge_max: float = Field(gt=0)
    soc_initial: float = Field(ge=0, le=1)
    soc_min: float = Field(ge=0, le=1)
    soc_max: float = Field(ge=0, le=1)
    charge_efficiency: float = Field(gt=0, le=1)
    discharge_efficiency: float = Field(gt=0, le=1)
    mobile_flag: bool = False

    @model_validator(mode="after")
    def valid_soc(self) -> "Storage":
        """Ensure the initial state lies within configured bounds."""
        if not self.soc_min <= self.soc_initial <= self.soc_max:
            raise ValueError("initial SOC outside bounds")
        return self

