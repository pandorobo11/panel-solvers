# Release and rollback

One release always contains the shared engine, both physical models, both
compatibility packages, and all six console commands.

## Prepare a release

1. Set `project.version` in `pyproject.toml` and run `uv lock`.
2. Move applicable `CHANGELOG.md` entries from `[Unreleased]` to a dated version
   section and retain a fresh `[Unreleased]` section.
3. Update current distribution-version references in README and current docs.
   Runtime artifacts for both domains will record the new distribution version.
   Do not change the FMF `1.3.8` or newtsolver `1.0.3` migration-baseline
   constants used by legacy signatures without a separate accepted decision.
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
panelsolver --help
panelsolver fmf --help
panelsolver hypersonic --help
fmfsolver-cli --help
newtsolver-cli --help
```

Keep input and output data during rollback, but do not treat data retention as
full input/output schema compatibility. The pinned legacy releases expose their
historical `.xls` input and NPZ output again. Before returning an old case table
to the current `panel-solvers` release, convert `.xls` to `.xlsx` or CSV and
remove the `save_npz_on` column.

Current Summary CSV output does not contain `save_npz_on` or `npz_path`, and the
current release does not create NPZ files. Existing VTP, NPZ, and CSV files are
left untouched during rollback and return. Exact audited build hashes and the
full transition probe are preserved in the
[Phase 8 execution record](../history/audits/PHASE8_EXECUTION_RECORD.md).
