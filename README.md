# panel-solvers

`panel-solvers` is the neutral, shared development repository for the existing
`fmfsolver` free-molecular-flow solver and `newtsolver` hypersonic panel solver.
It will provide one geometry/execution/integration platform while keeping the
Sentman and hypersonic physical models independent.

The repository is currently at **migration Phase 0**. It contains the package
boundaries, engineering rules, architecture decisions, and CI quality gates,
but intentionally contains no solver algorithm. Numerical code moves only after
Phase 1 fixes both legacy implementations as regression oracles.

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

The shared model boundary will return a per-panel local load vector, not only a
pressure coefficient. This is necessary to preserve the tangential contribution
of the Sentman model.

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

## Status and compatibility

No `fmfsolver` or `newtsolver` command is provided in Phase 0. The top-level
Python package names exist only to reserve their eventual compatibility
frontends. Continue using the legacy repositories for production calculations
until the relevant migration phase is accepted.
