"""newtsolver case-table compatibility policy."""

import importlib

from .exporters import export_vtp
from .io_cases import InputValidationError, ValidationIssue, read_cases

append_results_csv: object
validate_results_output_path: object
write_results_csv: object


def __getattr__(name: str):
    if name in {
        "append_results_csv",
        "validate_results_output_path",
        "write_results_csv",
    }:
        csv_out = importlib.import_module(f"{__name__}.csv_out")
        return getattr(csv_out, name)
    raise AttributeError(name)

__all__ = (
    "InputValidationError",
    "ValidationIssue",
    "append_results_csv",
    "export_vtp",
    "read_cases",
    "validate_results_output_path",
    "write_results_csv",
)
