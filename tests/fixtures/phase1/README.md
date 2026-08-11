# Phase 1 legacy baselines

These fixtures freeze the observable behavior of the immutable legacy commits
listed in `manifest.json`.  The four tiny ASCII STL files are byte-identical to
the copies in both legacy repositories.  Valid case tables always request both
VTP and NPZ so one capture contains the union of panel, state, integrated, and
metadata output.

`golden/<solver>/<case>.json` is a semantic snapshot, not a serialized artifact
golden.  It contains ordered CSV cells, VTP geometry/named cell and field arrays,
and NPZ named arrays with logical dtype, shape, and value.  The original VTP and
NPZ files are intentionally not committed.  In particular, trusted legacy NPZ
files are loaded with `allow_pickle=True` only during capture because their
`stl_paths` array has object dtype; committed JSON contains no pickle payload.

The generator validates UTC timestamps, nonnegative elapsed time, and agreement
among CSV, VTP, and recomputed case signatures before replacing those unstable
values with the documented markers in the manifest.  Absolute staging paths and
NumPy string-width dtypes are normalized for the same reason. Only values listed
under the manifest's `normalization` section are normalized.

Generate from clean sibling checkouts:

```bash
uv run python scripts/generate_phase1_goldens.py \
  --fmf-repo ../fmfsolver \
  --newt-repo ../newtsolver
```

Verify a clean regeneration without updating tracked expectations:

```bash
uv run python scripts/generate_phase1_goldens.py \
  --fmf-repo ../fmfsolver \
  --newt-repo ../newtsolver \
  --check
```

Both commands verify HEAD, origin URL, and tracked cleanliness, then `git
archive` each pinned commit into a temporary directory. They enforce Python 3.12,
run each full legacy unittest suite in `uv sync --locked --python 3.12`, and
separately capture forced rtree/Embree behavior in `uv sync --locked --python
3.12 --extra rayaccel`. The legacy checkouts are never installed into or written
by the process.

The subprocess environment removes inherited Python/virtual-environment state and
all six legacy solver variables, sets deterministic Python hashing, fixes CLI
formatting to `COLUMNS=80`/`LINES=24`, and gives GUI/font caches temporary
locations. Rooted Windows and POSIX paths are stored with the same marker and
POSIX suffix; JSON-encoded STL path lists are parsed before normalization.

To compare already-generated capture directories directly:

```bash
uv run python scripts/compare_phase1_goldens.py EXPECTED ACTUAL
```

Tolerance profiles are case-specific.  Discrete schema, topology, masks, names,
shapes, dtypes, strings, and metadata are exact.  Floating comparisons use the
quantity classes and evidence recorded in `manifest.json`; near-zero values use
the listed absolute tolerance rather than relative tolerance alone.

The generator validates every total/component row's shared signature and run
metadata, requires zero-offset UTC timestamps, and keeps blank CSV cells distinct
from explicit nonfinite tokens. Platform-specific `embreex`/`embreex4` package
identity is normalized only after the requested backend is proven available and
effective.
