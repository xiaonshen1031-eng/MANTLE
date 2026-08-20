"""Lexicographic exact-game value algebra."""

from __future__ import annotations

from dataclasses import dataclass

from .state import ExactState


@dataclass(frozen=True, order=True)
class GameValue:
    """Failure-first value followed by the safe-region secondary objectives."""

    failure: int = 0
    mission_degradation: float = 0.0
    eens: float = 0.0
    resource_use: float = 0.0
    switching: float = 0.0

    def add_stage(self, stage: tuple[float, float, float, float]) -> "GameValue":
        """Add a canonical stage cost while preserving failure priority."""

        return GameValue(
            self.failure,
            round(self.mission_degradation + float(stage[0]), 8),
            round(self.eens + float(stage[1]), 8),
            round(self.resource_use + float(stage[2]), 8),
            round(self.switching + float(stage[3]), 8),
        )

    def to_list(self) -> list[float | int]:
        """Return the comparison vector in its exact lexicographic order."""

        return [
            self.failure,
            self.mission_degradation,
            self.eens,
            self.resource_use,
            self.switching,
        ]


def terminal_value(state: ExactState) -> GameValue:
    """Assign terminal mission failure without weighted-sum scalarization."""

    failed = int(any(mission.state == "FAILED" for mission in state.missions))
    degraded = float(sum(mission.state != "NORMAL" for mission in state.missions))
    return GameValue(failed, degraded, 0.0, 0.0, 0.0)

