# panel-solvers

`panel-solvers` is the neutral, shared development repository for the existing
`fmfsolver` free-molecular-flow solver and `newtsolver` hypersonic panel solver.
It will provide one geometry/execution/integration platform while keeping the
Sentman and hypersonic physical models independent.

The repository has completed **migration Phase 7**. Phase 8, the independent
final audit, has not started.
Phase 1 freezes both legacy implementations as regression oracles, Phase 2
defines the immutable central contracts and model registry, and Phase 3 extracts
resolved-attitude/frame transforms, topology-preserving
mesh representation, common force/moment integration, component/result assembly,
semantic VTP/NPZ projection, and compatibility-preserving CSV projection/writing.
Thin product adapters verify already-computed legacy data through that full path.
Phase 4 adds the pinned Sentman and hypersonic equations behind independent
implementations of the common model contract. Phases 5–7 add the common
execution engine, scheduler, shared GUI/viewer, compatible case I/O and
artifacts, all six legacy commands, and the frozen Python import surfaces.

## Target structure

```text
src/
├── panelsolver/
│   ├── core/       # model-independent geometry, shielding, integration, execution
│   ├── models/     # independent Sentman and hypersonic physical models
│   └── app/        # shared CLI and GUI shell
├── fmfsolver/      # legacy compatibility frontend only
└── newtsolver/     # legacy compatibility frontend only
```

The shared model boundary returns a per-panel local load vector, not only a
pressure coefficient. This preserves the tangential contribution of the Sentman
model while representing Newton-family normal loads through the same API. The
exact contract is recorded in
[ADR 0002](docs/adr/0002-panel-load-vector-contract.md).

## Development setup

Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --locked --extra rayaccel
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run ruff check src tests scripts
uv build
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) before changing code. The migration
sequence is tracked in [docs/MIGRATION_PLAN.md](docs/MIGRATION_PLAN.md).

## Install and run

One `panel-solvers` wheel installs both compatible command families:

```bash
python -m pip install panel_solvers-0.1.0-py3-none-any.whl
fmfsolver-cli --input cases.csv
newtsolver-cli --input cases.csv
fmfsolver-gui
newtsolver-gui
```

The aliases `fmfsolver` and `newtsolver` also launch their respective GUIs.
Do not install this distribution beside either legacy distribution because the
top-level packages and commands overlap. The shared distribution version is
`0.1.0`; the deliberately independent public compatibility versions remain FMF
`1.3.8` and newtsolver `1.0.3`.

See [the Phase 7 user and release guide](docs/PHASE7_USER_GUIDE.md) for input,
output, environment, known-difference, release, and rollback details. Phase 7
acceptance evidence is in
[the execution record](docs/PHASE7_EXECUTION_RECORD.md). Numerical correctness,
performance, and lifecycle remain subject to the separate Phase 8 audit.
