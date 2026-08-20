"""Canonical public-history representation used by the reference tree."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class PublicHistory:
    """A legal sequence of public observations and common operator actions."""

    tokens: tuple[str, ...] = ()

    def extend(self, action_id: str, observation_id: str) -> "PublicHistory":
        """Return a new immutable history node."""

        return PublicHistory(self.tokens + (action_id, observation_id))

    @property
    def history_id(self) -> str:
        """Return a deterministic human-readable history identifier."""

        return "H0" if not self.tokens else "H_" + "__".join(self.tokens)

