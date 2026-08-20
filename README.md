# MANTLE

This repository provides the MANTLE implementation and MANTLE-ready datasets for
IEEE 14, IEEE 39, and RTS-GMLC.

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

The exact dynamic program operates on the reduced IEEE 14 information-state
model. IEEE 39 and RTS-GMLC use the shared coupled-system schema, conversion,
validation, communication, mission, and restoration-resource layers.

## Data layout

- `data/original/ieee14/case14.json`: pandapower 3.1.2 case14 source artifact.
- `data/original/ieee39/case39.json`: pandapower 3.1.2 case39 source artifact.
- `data/original/rts_gmlc`: frozen official RTS-GMLC source, MATPOWER,
  pandapower, and selected day-ahead time-series inputs.
- `data/modified/<system>`: deterministic MANTLE-ready coupled-system,
  communication, mission, restoration-resource, and provenance JSON files.

Third-party source information is stored with the data. The pandapower license
is at `third_party/pandapower/LICENSE`; the RTS-GMLC data notice is at
`data/original/rts_gmlc/repository_README.md`.

## Environment

Validated environment: 64-bit Windows 11, Python 3.11.9, and pip 25.2. The full
package table is in `ENVIRONMENT.md`.

### pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
```

### Conda

```powershell
conda env create -f environment.yml
conda activate mantle
python -m pip install -e . --no-deps
```

## Run and verify

```powershell
pytest -q
python scripts/run_ieee14_exact.py --budget 0 --horizon 1
python scripts/build_systems.py
```

`build_systems.py` regenerates `data/modified/<system>` from the bundled original
inputs and the configuration under `configs/`.
