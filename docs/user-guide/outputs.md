# Outputs

Each run can produce a summary CSV plus per-case VTP and NPZ files. The canonical
array and column inventory is in [Output formats](../reference/output-formats.md).

## Paths and switches

- If CLI `--output` is omitted, the summary is
  `<input_dir>/outputs/<input_stem>_result.csv`.
- Per-case artifacts are `<out_dir>/<case_id>.vtp` and
  `<out_dir>/<case_id>.npz`.
- `save_vtp_on` defaults to `1`; `save_npz_on` defaults to `0`.
- `out_dir` is created even if both artifact switches are off.

Both the final summary and checkpoint snapshots are written through a
same-directory temporary file, flushed, synchronized, and atomically replaced.
VTP/NPZ files already written remain after a later failure or cancellation.

## Summary rows

Every case emits a `total` row. A multi-STL case then emits one component row per
STL in component-ID order. Component rows have blank `vtp_path` and `npz_path`
because artifacts belong to the total case. Results remain in input order even
when workers finish out of order.

## Reading artifacts

VTP is intended for visualization and contains mesh-aligned cell data plus case
metadata. NPZ is intended for numerical post-processing and contains named
arrays and scalar values. Their contents overlap but are not identical; CSV is
the only output with component summary rows.

Compare artifacts semantically by field name, shape, metadata, and appropriate
numeric tolerance—not by file bytes. NPZ `stl_paths` is an object array inherited
from the compatibility format; load only trusted files when using
`allow_pickle=True`.
