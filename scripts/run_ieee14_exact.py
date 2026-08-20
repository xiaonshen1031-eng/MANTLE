"""Run the reduced IEEE 14 MANTLE exact solver without writing result files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mantle.exact.state import initial_state
from mantle.exact.value_functions import MantleExactSolver


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=0, choices=(0, 1, 2))
    parser.add_argument("--horizon", type=int, default=1)
    args = parser.parse_args()
    solver = MantleExactSolver(args.horizon)
    result = solver.solve((initial_state(args.budget),))
    print(json.dumps(solver.summary(result.worst), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
