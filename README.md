# MANTLE

This repository is a source-only package of the MANTLE implementation and the
three power-system inputs used by it. Experiment outputs, baseline
implementations, tuning pipelines, statistics, figures, and manuscript tooling
are intentionally excluded.

## Included implementation

- `src/mantle/exact`: finite-horizon information-state dynamic program,
  nonanticipative actions, state transition, lexicographic value, and DC
  feasibility oracle.
- `src/mantle/mechanisms`: mechanism signature, canonicalization, capability
  construction, exact partition refinement, quotient graph, and threat
  dominance.
- `src/mantle/envelope`: failure sets, predecessor recursion, antichain
  compression, threat envelope, and survivability calculation.
- `src/mantle/certificates`: safe-policy and failure-mechanism certificates.
- `src/mantle/systems`, `schemas`, `restoration`, `data`, `scenarios`, and
  `utilities`: coupled power/communication/mission/resource models, deterministic
  data conversion, validation, and reproducibility utilities.

The exact dynamic program is the frozen reduced IEEE 14 implementation. IEEE 39
and RTS-GMLC are included as complete coupled-system data packages and supported
by the common model/data layer; this repository does not claim that the reduced
IEEE 14 exact state space is a full-scale exact solver for those two systems.

## Data layout

- `data/original/ieee14/case14.json`: pandapower 3.1.2 case14 source artifact.
- `data/original/ieee39/case39.json`: pandapower 3.1.2 case39 source artifact.
- `data/original/rts_gmlc`: frozen official RTS-GMLC source, MATPOWER,
  pandapower, and selected day-ahead time-series inputs.
- `data/modified/<system>`: deterministic MANTLE-ready coupled-system,
  communication, mission, restoration-resource, and provenance JSON files.

`third_party/pandapower/LICENSE` covers the two bundled pandapower case files.
The RTS-GMLC data-use notice is retained verbatim in
`data/original/rts_gmlc/repository_README.md`. No license has been assigned to
the MANTLE source code in this整理版; publication to a public remote should wait
until the owner selects a code license.

## Setup and checks

```powershell
python -m pip install -e ".[test]"
pytest -q
python scripts/run_ieee14_exact.py --budget 0 --horizon 1
python scripts/build_systems.py
```

`build_systems.py` regenerates `data/modified/<system>` from the bundled original
inputs and the configuration under `configs/`. The repository does not contain
generated experiment results.

