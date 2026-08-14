# Output format reference

This page is the canonical inventory for the documented summary CSV, VTP, and
NPZ semantics. Serialization bytes, temporary filenames, and metadata ordering
inside container formats are not contracts.

## Summary CSV

The writer emits canonical input columns, then unknown input columns in their
source order, then the product's result columns.

FMF result columns, in order:

```text
solver_version, case_signature, run_started_at_utc, run_finished_at_utc,
run_elapsed_s, mode, out_S, out_Ti_K, out_attitude_input,
alpha_t_deg_resolved, beta_t_deg_resolved, scope, component_id,
component_stl_path, ray_backend_used, CA, CY, CN, Cl, Cm, Cn, CD, CL,
faces, shielded_faces, vtp_path, npz_path
```

newtsolver result columns, in order:

```text
solver_version, case_signature, run_started_at_utc, run_finished_at_utc,
run_elapsed_s, out_attitude_input, alpha_t_deg_resolved,
beta_t_deg_resolved, scope, component_id, component_stl_path,
ray_backend_used, CA, CY, CN, Cl, Cm, Cn, CD, CL, faces,
shielded_faces, vtp_path, npz_path
```

`scope` is `total` or `component`. A multi-STL case emits its total followed by
zero-based component IDs. Total/component coefficients use the same global
reference quantities. Product compatibility versions populate
`solver_version`.

## VTP

Cell arrays are aligned with mesh face order:

```text
C_face_stl, area_m2, center_x_stl_m, center_y_stl_m, center_z_stl_m,
shielded, stl_index, Cp_n, theta_deg
```

Common field data is:

```text
alpha_t_deg_resolved, attitude_input_used, beta_t_deg_resolved, case_id,
case_signature, ray_backend_used, solver_version, stl_count, stl_paths_json
```

newtsolver additionally stores `windward_eq_used` and `leeward_eq_used`. The
FMF-specific resolved thermal values are carried by NPZ and summary CSV, not VTP.

## NPZ

Common names are:

```text
Aref_m2, CA, CD, CL, CN, CY, C_M_body, C_force_body, C_force_stl,
Cl, Cm, Cn, Vhat_stl, alpha_t_deg_resolved, areas_m2, attitude_input,
beta_t_deg_resolved, centers_stl_m, face_stl_index, faces,
normals_out_stl, ray_backend_used, shielded, stl_paths, vertices, Cp_n
```

FMF additionally stores `S`, `Ti_K`, and `Tw_K`. NPZ does not store case ID,
case signature, compatibility version, `C_face_stl`, `theta_deg`, or newtsolver
equation metadata. Current solver-generated `panel-solvers` output stores
`stl_paths` as a NumPy Unicode or byte-string array, so the complete NPZ can be
loaded with `allow_pickle=False`.

NPZ files written by the pinned legacy distributions may instead contain an
object-dtype `stl_paths` array. Load such a file with `allow_pickle=True` only
when the file is trusted; this exception is not required for current output.

## Coefficient and path semantics

`CA`, `CY`, `CN`, `Cl`, `Cm`, `Cn`, `CD`, and `CL` follow
[Numerical conventions](numerical-conventions.md). Disabled artifact paths and
component artifact paths are empty strings in the summary. See
[Outputs](../user-guide/outputs.md) for lifecycle and durability behavior.
