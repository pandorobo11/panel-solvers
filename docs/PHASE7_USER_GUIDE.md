# Phase 7 user, release, and rollback guide

Phase 7 provides one `panel-solvers` distribution containing the shared engine,
both physical models, both compatibility packages, and all six old command
names. It does not deprecate the old names or perform the Phase 8 audit.

## Install or migrate

Python 3.12 or newer is required. The new wheel and either legacy distribution
must not coexist because they provide overlapping `fmfsolver`/`newtsolver`
packages and commands.

```bash
python -m pip uninstall fmfsolver newtsolver panel-solvers
python -m pip install panel_solvers-0.1.0-py3-none-any.whl
```

Install the platform's `rayaccel` extra when installing from a source/index that
exposes extras. A forced `embree` case remains an error if Embree is unavailable;
it never silently falls back. `rtree` remains supported.

One distribution version and two compatibility versions are intentional:

- `importlib.metadata.version("panel-solvers")` returns `0.1.0`;
- `fmfsolver.__version__` returns the frozen FMF value `1.3.8`;
- `newtsolver.__version__` returns the frozen newtsolver value `1.0.3`.

## Commands

`fmfsolver` and `fmfsolver-gui` open `Sentman FMF Solver (GUI)`;
`newtsolver` and `newtsolver-gui` open `newtsolver (GUI)`. Batch use is:

```bash
fmfsolver-cli --input cases.csv --output results.csv --workers 1
newtsolver-cli --input cases.csv --output results.csv --workers 1
```

Both CLIs accept `--cases` with space- or comma-separated case IDs and
`--flush-every-cases N` for complete input-ordered checkpoint snapshots. Zero
disables checkpoints; the default is 100. If `--output` is omitted, the result
is `<input_dir>/outputs/<input_stem>_result.csv`. The retained D008 difference is
visible in help: FMF requires at least one value after `--cases`, while
newtsolver accepts an empty list.

## Input

CSV, XLSX, XLSM, and XLS are accepted. Paths in `stl_path` and `out_dir` are
resolved relative to the input table. Semicolons preserve ordered multi-
component STL and newtsolver equation lists. The committed unchanged examples
are `tests/fixtures/phase1/inputs/fmfsolver_cases.csv` and
`tests/fixtures/phase1/inputs/newtsolver_cases.csv`.

Common required fields are `case_id`, `stl_path`, `stl_scale_m_per_unit`,
attitude angles, the three reference coordinates, `Aref_m2`, and three reference
lengths. FMF additionally selects either Mode A (`S` and `Ti_K`) or Mode B
(`Mach` and `Altitude_km`) and requires `Tw_K`. newtsolver requires `Mach` and
`gamma` and accepts independent windward/leeward equations. The exact ordered
schemas, defaults, and validation rules are in the product `io/io_cases.py`
adapters and frozen by Phase 1 compatibility tests.

The products deliberately retain different XLS dispatch, case-ID/duplicate,
and `beta_tan` angle-domain rules. Do not normalize one input merely because it
is accepted by the other.

## Output

The summary CSV preserves each product's exact columns, order, total/component
rows, blanks, collision scope, and atomic-write policy. `save_vtp_on` and
`save_npz_on` select per-case artifacts under `out_dir`; the directory side
effect is retained even when both flags are off.

VTP stores geometry, panel scalars, shielding, case identity/signature, resolved
attitude, backend, compatibility version, and product-only metadata. NPZ stores
the accepted named numerical arrays and product-only values. Formats are
compared semantically by name, shape, metadata, and quantity-specific tolerance,
not by file bytes. The precise inventory is in
`phase1/BEHAVIORAL_INVENTORY.md` and the tolerances are in
`phase1/TOLERANCES.md`.

## Environment precedence

For every setting, an explicit API/configuration argument wins. The neutral
name then wins over the prefix belonging to the selected product; core never
mixes both product prefixes:

| Setting | Order after explicit argument | Default |
|---|---|---:|
| shielding cache maximum | `PANELSOLVER_SHIELD_CACHE_MAX`, then `FMFSOLVER_SHIELD_CACHE_MAX` or `NEWTSOLVER_SHIELD_CACHE_MAX` | 1; 0 disables |
| shielding ray batch | `PANELSOLVER_SHIELD_BATCH_SIZE`, then selected legacy prefix | Embree 64; rtree 8 |
| scheduler chunk cases | `PANELSOLVER_PARALLEL_CHUNK_CASES`, then selected legacy prefix | 8 |

Values must be integers in the documented positive/nonnegative domain. If a
later case in one worker chunk raises a caught Python exception, FMF forwards
worker logs but discards earlier completed results from that chunk. newtsolver
drops worker logs but yields those completed cases before reporting the worker
error. Yielded cases update progress and reach a CSV checkpoint only when the
configured flush interval is met; neither product emits a final snapshot after
the error. Already-written per-case artifacts are not rolled back by either
policy.

## Known retained differences

Phase 7 does not choose between product contracts. Notable retained differences
include XLS dispatch, case IDs and duplicate comparison, FMF's stricter
`beta_tan` domain, mesh repair, CLI `--cases`, output collision and CSV
durability, parallel logs/partial results, legacy signatures, model-only
CSV/VTP/NPZ fields, GUI titles/overlays/close behavior, and D025 Python exports.
The authoritative ledger is `phase1/LEGACY_DIFFERENCES.md`; accepted Phase 7
handling is summarized in `PHASE7_COMPATIBILITY.md`.

## Release

1. Update `project.version` and release notes in a reviewable change.
2. Run the locked full suite, Ruff, build, built-wheel reinstall/smoke, both
   unchanged samples, and both manual macOS GUI smokes.
3. Require successful Ubuntu, Windows, macOS, and artifact CI.
4. Create exactly `v<project.version>` only after those gates pass.
5. The tag workflow rebuilds and publishes the wheel and source distribution in
   one GitHub Release. Both products always ship together.

No Phase 7 acceptance tag is created automatically by the migration PR.

## Rollback

Keep input and result files; rollback does not require converting them. Remove
the shared distribution before restoring either legacy distribution:

```bash
python -m pip uninstall panel-solvers
python -m pip install /path/to/pinned-fmfsolver-artifact
python -m pip install /path/to/pinned-newtsolver-artifact
```

Use artifacts matching the commits recorded in `MIGRATION_SOURCES.md`. Verify
the command resolved on `PATH` and run one known case for each product. Never
layer a legacy wheel over `panel-solvers`. The legacy repositories remain
unarchived until the independent Phase 8 audit is accepted.
