# Development guide

## Scope of this repository

This repository migrates two mature numerical applications into a shared engine.
Until a feature has passed its migration acceptance criteria, the corresponding
legacy repository remains the production implementation and numerical oracle.

Use Python 3.12 or newer. `uv.lock` is authoritative for local development and
CI. Do not replace `unittest`, make GUI dependencies optional, or add broad type
checking as incidental migration work; those changes require separate proposals.

## Set up

```bash
uv sync --locked --extra rayaccel
```

The `rayaccel` extra installs the platform-specific Embree binding. CI requires
Embree on Linux, Windows, and Apple-silicon macOS. The rtree path must remain
testable because it is a supported runtime fallback.

Legacy source is read-only. Use sibling checkouts when they match
`MIGRATION_SOURCES.md`, or place ignored checkouts under `.reference/`.

## Standard workflow

1. Read `AGENTS.md`, this guide, the architecture and compatibility documents,
   relevant ADRs, and the issue.
2. Confirm the target legacy commits and record any drift before editing.
3. State the files to change, proposed behavior, and numerical/compatibility risk.
4. Make the smallest reviewable change and add tests with it.
5. Run targeted tests, then all standard quality gates.
6. Inspect the diff for accidental format, API, data-schema, or golden changes.
7. Report evidence, numeric deltas, compatibility effects, and unresolved risks.

## Quality gates

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run ruff check src tests scripts
uv build
```

For packaging changes, reinstall the built wheel into the managed environment and
run imports and command `--help` outside the repository working directory. For GUI
changes, add a headless-safe test where practical and document the manual smoke
test. For numerical work, run the affected golden cases with both ray backends
where shielding can influence the result.

CI runs the locked environment, Embree availability check, unittest suite, and
Ruff on Ubuntu, Windows, and macOS. A separate Linux job builds, reinstalls, and
imports the wheel. Release tags must equal `v` plus `project.version`.

## Tests and fixtures

- `tests/unit`: small model-independent contracts and utilities.
- `tests/regression`: semantic numerical golden comparisons.
- `tests/compatibility`: legacy command, Python API, case, and artifact contracts.
- `tests/gui`: shared GUI/viewer behavior.
- `tests/fixtures`: compact source inputs and generated expectations.

Every generated golden fixture must carry provenance: source repository, commit,
Python/dependency context when material, exact command/case, backend, and numeric
tolerance. Prefer text or compressed NumPy data that reviewers can inspect. Do
not compare VTP/NPZ files byte-for-byte.

Phase 1 legacy captures live under `tests/fixtures/phase1`. Regenerate or verify
them with `scripts/generate_phase1_goldens.py`; the semantic format and command
are documented in `tests/fixtures/phase1/README.md`, and the evidence-based
quantity limits are in `docs/phase1/TOLERANCES.md`.

## Versioning and releases

The unified distribution begins at `0.1.0` while migration is incomplete. A tag
must be `v<project.version>`. Compatibility command/package versions and the
shared distribution strategy remain governed by the migration plan; do not infer
compatibility from this initial version.
