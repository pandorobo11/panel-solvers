"""Frozen FMF DataFrame CSV calls over shared writer policy."""

from panelsolver._compat.legacy_results import (
    append_legacy_results_csv,
    write_legacy_results_csv,
)

from ..csv_adapter import CSV_WRITE_POLICY
from .io_cases import INPUT_COLUMN_ORDER


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


__all__ = ("append_results_csv", "write_results_csv")
