# Release and rollback

One release always contains the shared engine, both physical models, both
compatibility packages, and all six console commands.

## Prepare a release

1. Set `project.version` in `pyproject.toml` and run `uv lock`.
2. Move applicable `CHANGELOG.md` entries from `[Unreleased]` to a dated version
   section and retain a fresh `[Unreleased]` section.
3. Update current distribution-version references in README and current docs.
   Do not change FMF `1.3.8` or newtsolver `1.0.3` without a separate accepted
   compatibility decision.
4. Run the locked unit/regression/compatibility/GUI suite, Ruff, build, and clean
   installed-wheel smoke tests for both products.
5. Tag only the protected accepted `main` commit as `v<project.version>`.

`CHANGELOG.md` is the source of truth for release notes. CI publishes the exact
tested artifacts only after all platform and artifact gates pass.

## Roll back to pinned legacy implementations

The shared distribution and legacy distributions must not coexist. Pinned source
commits are recorded in
[Migration sources](../history/migration/MIGRATION_SOURCES.md). The repository's
`scripts/probe_legacy_rollback.py` verifies those commits and can build recorded
rollback wheels from clean local sources or official HTTPS URLs.

Operational order:

```bash
python -m pip uninstall panel-solvers
python -m pip install /path/to/fmfsolver-1.3.8-*.whl /path/to/newtsolver-1.0.3-*.whl
```

Return to the shared distribution in the opposite order:

```bash
python -m pip uninstall fmfsolver newtsolver
python -m pip install /path/to/panel_solvers-<version>-py3-none-any.whl
fmfsolver-cli --help
newtsolver-cli --help
```

Keep input and output data during rollback; documented formats remain compatible.
Exact audited build hashes and the full transition probe are preserved in the
[Phase 8 execution record](../history/audits/PHASE8_EXECUTION_RECORD.md).
