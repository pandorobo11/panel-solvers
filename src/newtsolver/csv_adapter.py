"""Phase 3 newtsolver summary CSV compatibility policies."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from panelsolver.app.csv_writer import (
    AtomicCsvWritePolicy,
    TempNameStyle,
    validate_csv_output_path,
    write_csv_atomic,
)
from panelsolver.core import CommonResults
from panelsolver.core.csv_projection import (
    CsvCell,
    CsvProjection,
    CsvProjectionPolicy,
    project_summary_csv,
)

CSV_PROJECTION_POLICY = CsvProjectionPolicy(
    input_columns=(
        "case_id",
        "stl_path",
        "stl_scale_m_per_unit",
        "Mach",
        "gamma",
        "windward_eq",
        "leeward_eq",
        "alpha_deg",
        "beta_or_bank_deg",
        "attitude_input",
        "ref_x_m",
        "ref_y_m",
        "ref_z_m",
        "Aref_m2",
        "Lref_Cl_m",
        "Lref_Cm_m",
        "Lref_Cn_m",
        "shielding_on",
        "ray_backend",
        "out_dir",
        "save_vtp_on",
        "save_npz_on",
    ),
    result_columns=(
        "solver_version",
        "case_signature",
        "run_started_at_utc",
        "run_finished_at_utc",
        "run_elapsed_s",
        "out_attitude_input",
        "alpha_t_deg_resolved",
        "beta_t_deg_resolved",
        "scope",
        "component_id",
        "component_stl_path",
        "ray_backend_used",
        "CA",
        "CY",
        "CN",
        "Cl",
        "Cm",
        "Cn",
        "CD",
        "CL",
        "faces",
        "shielded_faces",
        "vtp_path",
        "npz_path",
    ),
)
CSV_WRITE_POLICY = AtomicCsvWritePolicy(
    temp_name_style=TempNameStyle.UUID,
    fsync_before_replace=False,
)


def project_csv(
    input_row: Mapping[str, CsvCell],
    results: CommonResults,
    *,
    run_values: Mapping[str, CsvCell],
    component_sources: Mapping[int, str] | None = None,
) -> CsvProjection:
    return project_summary_csv(
        input_row,
        results,
        CSV_PROJECTION_POLICY,
        run_values=run_values,
        component_sources=component_sources,
    )


def validate_results_output_path(
    out_path: str | Path,
    input_path: str | Path,
    case_rows: Iterable[Mapping[str, object]],
) -> Path:
    """Preserve D009: protect input, STL, and planned VTP/NPZ paths."""
    protected: list[str | Path] = [input_path]
    for row in case_rows:
        for raw_stl in str(row.get("stl_path", "")).split(";"):
            if raw_stl.strip():
                protected.append(raw_stl.strip())
        out_dir = Path(str(row.get("out_dir", "outputs"))).expanduser().resolve()
        case_id = str(row.get("case_id", "")).strip()
        if case_id:
            protected.extend((out_dir / f"{case_id}.vtp", out_dir / f"{case_id}.npz"))
    return validate_csv_output_path(out_path, protected)


def write_csv(out_path: str | Path, projection: CsvProjection) -> None:
    write_csv_atomic(out_path, projection, CSV_WRITE_POLICY)


__all__ = (
    "CSV_PROJECTION_POLICY",
    "CSV_WRITE_POLICY",
    "project_csv",
    "validate_results_output_path",
    "write_csv",
)
