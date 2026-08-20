"""Complete and incomplete observation schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ObservationRecord(BaseModel):
    """Reported state that never embeds hidden truth in observed fields."""

    model_config = ConfigDict(extra="forbid")
    stage: int = Field(ge=0)
    observed_component_status: dict[str, bool | str]
    unknown_component_status: list[str]
    delayed_component_status: list[str]
    communication_reachability: dict[str, bool]
    measurement_availability: dict[str, bool]
    observation_id: str
    observation_equivalence_identifier: str

