# panel-solvers

`panel-solvers` is the neutral, shared development repository for the existing
`fmfsolver` free-molecular-flow solver and `newtsolver` hypersonic panel solver.
It will provide one geometry/execution/integration platform while keeping the
Sentman and hypersonic physical models independent.

The repository has completed **migration Phase 2**, and Phase 3 is in progress.
Phase 1 freezes both legacy implementations as regression oracles, Phase 2
defines the immutable central contracts and model registry, and the initial
Phase 3 slices extract resolved-attitude/frame transforms, topology-preserving
mesh representation, common force/moment integration, component/result assembly,
semantic VTP/NPZ projection, and compatibility-preserving CSV projection/writing.
It does not contain a physical-model equation or a runnable solver pipeline.

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

## Status and compatibility

No `fmfsolver` or `newtsolver` command is provided yet. The top-level Python
package names exist only to reserve their eventual compatibility frontends.
Continue using the legacy repositories for production calculations until the
relevant migration phase is accepted.
