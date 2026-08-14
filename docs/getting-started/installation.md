# Installation

## Requirements

- Python 3.12 or newer
- A platform supported by the required Python dependencies, including Qt,
  PyVista/VTK, Trimesh, SciPy, pandas, and rtree
- An STL mesh and a CSV or Excel case table

## Install from a checkout

For normal use:

```bash
python -m pip install .
```

To add the platform-specific Embree binding used by the accelerated ray backend:

```bash
python -m pip install '.[rayaccel]'
```

For a reproducible development environment, use the locked setup instead:

```bash
uv sync --locked --extra rayaccel
```

Commands in that environment can be prefixed with `uv run`.

## Verify the installation

```bash
fmfsolver-cli --help
newtsolver-cli --help
python -c 'import importlib.metadata as m; print(m.version("panel-solvers"))'
```

The command above reports the installed distribution version dynamically. The
values exposed by `fmfsolver.__version__` (`1.3.8`) and
`newtsolver.__version__` (`1.0.3`) are separate compatibility versions.

## Legacy-distribution coexistence

Do not install this distribution in the same environment as either legacy
`fmfsolver` or `newtsolver` distribution. All of them provide overlapping
top-level packages and console commands. Remove the legacy packages first:

```bash
python -m pip uninstall fmfsolver newtsolver
python -m pip install .
```

Operational rollback is documented separately in
[Release and rollback](../development/release-and-rollback.md).
