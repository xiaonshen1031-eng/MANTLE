# Environment

## Validated platform

- Operating system: Microsoft Windows 11 64-bit, version 10.0.26200
- Python: 3.11.9
- pip: 25.2

## Runtime packages

| Package | Version | Role |
|---|---:|---|
| NumPy | 2.2.6 | Numerical arrays and deterministic state calculations |
| pandas | 2.2.3 | RTS-GMLC tabular and time-series input processing |
| SciPy | 1.16.0 | Linear-programming feasibility oracle |
| NetworkX | 3.6.1 | Communication topology and reachability |
| Pydantic | 2.11.7 | Coupled-system schema validation |
| PyYAML | 6.0.2 | Configuration loading |
| pandapower | 3.1.2 | IEEE and RTS power-network loading and AC validation |
| pytest | 8.4.1 | Source and data-package verification |

`requirements.txt` contains runtime dependencies. `requirements-dev.txt` adds
the verification dependency. `environment.yml` creates the equivalent Conda
environment.

