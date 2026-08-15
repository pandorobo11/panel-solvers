# panel-solvers

`panel-solvers` is a single Python distribution for two STL panel-method flow
domains:

| Canonical domain | Use it for | Physical model or methods |
|---|---|---|
| `fmf` | Free-molecular and rarefied-flow surface loads | Sentman |
| `hypersonic` | Hypersonic pressure loads | Newtonian-family methods |

Choose FMF when molecular thermal interaction and tangential surface load matter.
Choose Hypersonic for continuum pressure estimates using Newtonian,
modified Newtonian, tangent-wedge, tangent-cone, or Prandtl–Meyer methods. See
[Choosing a solver](docs/index.md#choosing-a-solver) for the model limits.

## Requirements and installation

Python 3.12 or newer is required. From a checkout:

```bash
python -m pip install .
```

For the optional accelerated Embree ray backend:

```bash
python -m pip install '.[rayaccel]'
```

The built-in `rtree` backend remains supported. Do not install `panel-solvers`
beside the legacy `fmfsolver` or `newtsolver` distributions because their package
and command names overlap. See the [installation guide](docs/getting-started/installation.md).

## Run

Launch either canonical GUI, then select its example case file:

```bash
panelsolver-gui fmf
panelsolver-gui hypersonic
```

Run the same examples without the GUI:

```bash
panelsolver fmf --input examples/fmfsolver/basic.csv --workers 1 --flush-every-cases 0
panelsolver hypersonic --input examples/newtsolver/basic.csv --workers 1 --flush-every-cases 0

# Legacy compatibility commands remain available:
fmfsolver-cli --input examples/fmfsolver/basic.csv --workers 1 --flush-every-cases 0
newtsolver-cli --input examples/newtsolver/basic.csv --workers 1 --flush-every-cases 0
```

`fmf` is the free-molecular-flow domain selector; it is not the legacy
`fmfsolver` product identity. The selected physical model is Sentman.

Case tables may be CSV, XLSX, or XLSM files.

The six `fmfsolver` / `newtsolver` commands remain legacy compatibility entry
points with unchanged versions, behavior, and GUI titles.
Results are written below each example's `outputs/` directory. The
[quickstart](docs/getting-started/quickstart.md) explains the files and the main
CLI options.

## Documentation

- [Documentation home](docs/index.md)
- [GUI guide](docs/user-guide/gui.md) and [CLI guide](docs/user-guide/cli.md)
- [Case-file guide](docs/user-guide/case-files.md)
- [FMF](docs/solvers/fmfsolver.md) and
  [Hypersonic](docs/solvers/newtsolver.md)
- [FMF input](docs/reference/fmfsolver-input.md),
  [Hypersonic input](docs/reference/newtsolver-input.md), and
  [output reference](docs/reference/output-formats.md)
- [Development guide](docs/development/setup-and-testing.md)
- [Migration and audit history](docs/history/README.md)

## Status and compatibility

The FMF/Hypersonic integration and Phase 8 audit are complete. One
`panel-solvers` distribution (currently `0.1.0`) provides the canonical
`panelsolver` and `panelsolver-gui` command namespaces plus all six legacy
compatibility command names. Product-facing
compatibility versions remain FMF `1.3.8` and
newtsolver `1.0.3`. Supported commands, normal GUI use, documented case files,
and documented Summary CSV/VTP semantics are compatibility surfaces. The small
`panelsolver` package-root Python API is stable; lower-level architecture APIs,
legacy direct-Python compatibility, and private implementation have distinct
support levels. See the
[compatibility policy](docs/reference/compatibility.md) and
[CHANGELOG.md](CHANGELOG.md).
