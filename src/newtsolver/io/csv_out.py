"""Frozen newtsolver DataFrame CSV calls over shared writer policy."""

from panelsolver.app.legacy_results import (
    append_legacy_results_csv,
    write_legacy_results_csv,
)

from ..csv_adapter import CSV_WRITE_POLICY
from ..csv_adapter import validate_results_output_path as _validate
from .io_cases import INPUT_COLUMN_ORDER


def validate_results_output_path(out_path, input_path, df_cases):
    return _validate(out_path, input_path, df_cases.to_dict(orient="records"))


def write_results_csv(out_path: str, df_in, df_out) -> None:
    write_legacy_results_csv(
        out_path,
        df_in,
        df_out,
        input_column_order=INPUT_COLUMN_ORDER,
        policy=CSV_WRITE_POLICY,
    )


def append_results_csv(out_path: str, df_in, df_out) -> None:
    append_legacy_results_csv(
        out_path,
        df_in,
        df_out,
        input_column_order=INPUT_COLUMN_ORDER,
    )


__all__ = (
    "append_results_csv",
    "validate_results_output_path",
    "write_results_csv",
)
