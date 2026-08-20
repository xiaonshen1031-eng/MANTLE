"""Deterministic seed derivation without Python hash randomization."""

from dataclasses import dataclass
import hashlib
import random
import numpy as np


@dataclass(frozen=True)
class SeedManager:
    """Derive stable child seeds from one root seed and named namespaces."""

    root_seed: int

    def child_seed(self, namespace: str) -> int:
        """Return a deterministic unsigned 32-bit child seed."""
        digest = hashlib.sha256(f"{self.root_seed}:{namespace}".encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big", signed=False)

    def rng(self, namespace: str) -> np.random.Generator:
        """Return a NumPy generator for a stable namespace."""
        return np.random.default_rng(self.child_seed(namespace))

    def apply_global(self) -> None:
        """Seed Python and NumPy legacy global generators."""
        random.seed(self.root_seed)
        np.random.seed(self.root_seed)

