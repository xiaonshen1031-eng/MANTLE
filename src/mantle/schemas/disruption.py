"""Compound-disruption scenario schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DisruptionAction(BaseModel):
    """Abstract consequence-level disruption action."""

    model_config = ConfigDict(extra="forbid")
    action_id: str
    stage: int = Field(ge=0)
    layer: str
    target_type: str
    target_id: str
    abstract_cost: int = Field(ge=1)
    effect_type: str
    effect_duration: int = Field(ge=1)
    observation_visibility: str
    secondary_disruption_flag: bool = False


class Scenario(BaseModel):
    """Serializable deterministic scenario definition."""

    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    system_id: str
    family: str
    seed: int
    horizon: int = Field(gt=0)
    budget: int = Field(ge=1)
    initial_disruption_stage: int = Field(ge=0)
    secondary_disruption_stage: int | None = None
    action_list: list[DisruptionAction]
    total_abstract_cost: int = Field(ge=0)
    observation_mode: str
    restoration_resource_configuration: str
    metadata: dict[str, str | int | bool]

    @model_validator(mode="after")
    def budget_is_respected(self) -> "Scenario":
        """Reject scenarios that exceed or misreport the abstract budget."""
        actual = sum(a.abstract_cost for a in self.action_list)
        if actual != self.total_abstract_cost or actual > self.budget:
            raise ValueError("scenario abstract budget is inconsistent")
        return self

