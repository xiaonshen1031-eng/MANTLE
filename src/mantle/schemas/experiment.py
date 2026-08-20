"""Global experiment configuration schema."""

from pydantic import BaseModel, ConfigDict, Field


class GlobalConfig(BaseModel):
    """Validated global configuration with no hidden numerical parameters."""

    model_config = ConfigDict(extra="forbid")
    project_name: str
    phase: int = Field(ge=1)
    random_seed: int
    numpy_seed: int
    python_seed: int
    solver_name: str
    solver_threads: int = Field(ge=1)
    solver_time_limit: int = Field(gt=0)
    mip_gap: float = Field(ge=0)
    numerical_tolerance: float = Field(gt=0)
    logging_level: str
    output_directory: str
    save_intermediate_states: bool
    strict_validation: bool
    event_order: list[str]

