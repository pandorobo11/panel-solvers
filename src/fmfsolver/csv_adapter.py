"""Legacy forwarding surface for canonical FMF projection policy."""

from panelsolver.domains.fmf import (
    CSV_PROJECTION_POLICY,
    CSV_WRITE_POLICY,
    project_csv,
    validate_results_output_path,
    write_csv,
)

__all__ = (
    "CSV_PROJECTION_POLICY",
    "CSV_WRITE_POLICY",
    "project_csv",
    "validate_results_output_path",
    "write_csv",
)
