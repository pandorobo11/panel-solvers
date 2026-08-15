# panel-solvers

`panel-solvers` is a single Python distribution for two STL panel-method
applications:

| Command family | Use it for | Physical model |
|---|---|---|
| `fmfsolver` | Free-molecular and rarefied-flow surface loads | Sentman |
| `newtsolver` | Hypersonic pressure loads | Newtonian-family methods |

Choose FMF when molecular thermal interaction and tangential surface load matter.
Choose newtsolver for continuum hypersonic pressure estimates using Newtonian,
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

Launch either GUI, then select its example case file:

```bash
fmfsolver-gui
newtsolver-gui
```

Run the same examples without the GUI:

```bash
fmfsolver-cli --input examples/fmfsolver/basic.csv --workers 1 --flush-every-cases 0
newtsolver-cli --input examples/newtsolver/basic.csv --workers 1 --flush-every-cases 0
```

Case tables may be CSV, XLSX, or XLSM files.

The aliases `fmfsolver` and `newtsolver` also launch their respective GUIs.
Results are written below each example's `outputs/` directory. The
[quickstart](docs/getting-started/quickstart.md) explains the files and the main
CLI options.

## Documentation

- [Documentation home](docs/index.md)
- [GUI guide](docs/user-guide/gui.md) and [CLI guide](docs/user-guide/cli.md)
- [Case-file guide](docs/user-guide/case-files.md)
- [FMF solver](docs/solvers/fmfsolver.md) and
  [newtsolver](docs/solvers/newtsolver.md)
- [FMF input](docs/reference/fmfsolver-input.md),
  [newtsolver input](docs/reference/newtsolver-input.md), and
  [output reference](docs/reference/output-formats.md)
- [Development guide](docs/development/setup-and-testing.md)
- [Migration and audit history](docs/history/README.md)

## Status and compatibility

The FMF/newtsolver integration and Phase 8 audit are complete. One
`panel-solvers` distribution (currently `0.1.0`) provides all six compatible
command names. Product-facing compatibility versions remain FMF `1.3.8` and
newtsolver `1.0.3`. Supported commands, normal GUI use, documented case files,
and documented Summary CSV/VTP semantics are compatibility surfaces; direct Python
implementation details are best effort. See the
[compatibility policy](docs/reference/compatibility.md) and
[CHANGELOG.md](CHANGELOG.md).
