# Release and rollback

One release always contains the shared engine, both physical models, both
compatibility packages, and all six console commands.

## Version policy

`project.version` in `pyproject.toml` is the sole source of truth for the shared
distribution version. The editable `panel-solvers` entry in `uv.lock` must match
it. `CHANGELOG.md` is the source of truth for release notes, and the release tag
is an annotated `v<project.version>` tag on the accepted protected `main` commit.
FMF `1.3.8` and newtsolver `1.0.3` remain independent compatibility versions;
they are not distribution-version aliases.

Distribution versions follow both SemVer intent and PEP 440 spelling:

- patch: backward-compatible bug fixes and documentation, GUI-presentation, or
  distribution-processing changes only;
- minor: backward-compatible features and intentional numerical-behavior
  changes;
- major: breaking changes after the first stable release;
- release candidate: for example `0.1.0rc1`;
- development version: for example `0.1.1.dev0`.

An intentional numerical-result change is never classified as a routine patch.
Its model algorithm version, case signature, cache identity, artifact metadata,
compatibility plan, and regression tolerances must each be assessed explicitly.

## Prepare a release

1. Set `project.version` in `pyproject.toml` and run `uv lock`; verify the
   `panel-solvers` version in `uv.lock` matches.
2. Move applicable `CHANGELOG.md` entries from `[Unreleased]` to a dated version
   section and retain a fresh `[Unreleased]` section.
3. Update only checklist or release-note locations that intentionally record a
   concrete distribution version. Runtime displays must use
   `importlib.metadata.version("panel-solvers")`. Do not change FMF `1.3.8` or
   newtsolver `1.0.3` without a separate accepted compatibility decision.
4. Run the locked unit/regression/compatibility/GUI suite, Ruff, build, and clean
   installed-wheel smoke tests for both products.
5. Tag only the protected accepted `main` commit as `v<project.version>`.

`CHANGELOG.md` is the source of truth for release notes. CI publishes the exact
tested wheel, sdist, offline documentation ZIP, examples ZIP, and manifest only
after all platform and artifact gates pass. The release job downloads this set
and does not rebuild it. The documentation ZIP is assembled from the exact
site stored in the wheel, so its files are byte-identical to the GUI help site.

The distribution manifest uses schema v2. Its ordered artifact records identify
the `wheel`, `sdist`, `docs_zip`, and `examples_zip` by kind, exact filename, and
SHA-256; the wheel record also preserves its METADATA name and version. The
manifest binds the set to the GitHub commit SHA. Verification rejects missing or
extra release files, duplicate or reordered kinds, renamed files, altered hashes,
wheel metadata mismatches, and a different expected commit.

Before the first public release, resolve every blocking item in the
[release-readiness audit](release-readiness-audit.md).

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
