"""Phase 3 FMF summary CSV compatibility policies."""

from __future__ import annotations

from collections.abc import Mapping
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
        "S",
        "Ti_K",
        "Mach",
        "Altitude_km",
        "Tw_K",
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
        "mode",
        "out_S",
        "out_Ti_K",
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
    temp_name_style=TempNameStyle.NAMED_RANDOM,
    fsync_before_replace=True,
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
) -> Path:
    """Preserve D009: FMF protects only the selected input table."""
    return validate_csv_output_path(out_path, (input_path,))


def write_csv(out_path: str | Path, projection: CsvProjection) -> None:
    write_csv_atomic(out_path, projection, CSV_WRITE_POLICY)


__all__ = (
    "CSV_PROJECTION_POLICY",
    "CSV_WRITE_POLICY",
    "project_csv",
    "validate_results_output_path",
    "write_csv",
)
