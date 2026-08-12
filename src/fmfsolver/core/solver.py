"""Frozen FMF direct solver API over the shared Phase 7 runtime."""

from __future__ import annotations

import pandas as pd

from panelsolver.app.legacy_results import direct_legacy_result, run_legacy_cases
from panelsolver.app.legacy_scheduler import legacy_execution_order

from ..csv_adapter import CSV_PROJECTION_POLICY
from ..runtime import run_cases as _runtime_run_cases
from .case_signature import build_case_signature

_RENAMES = {
    "out_S": "S",
    "out_Ti_K": "Ti_K",
    "out_attitude_input": "attitude_input",
}


def _build_execution_order(df: pd.DataFrame) -> list[int]:
    return legacy_execution_order(df, strict=True)


def run_case(row: dict, logfn) -> dict:
    result = run_cases(pd.DataFrame([row]), logfn, workers=1)
    return direct_legacy_result(result)


def run_cases(
    df: pd.DataFrame,
    logfn,
    workers: int = 1,
    progress_cb=None,
    cancel_cb=None,
    flush_every_cases: int | None = None,
    chunk_cb=None,
) -> pd.DataFrame:
    return run_legacy_cases(
        df,
        _runtime_run_cases,
        legacy_env_prefix="FMFSOLVER",
        input_columns=CSV_PROJECTION_POLICY.input_columns,
        renames=_RENAMES,
        legacy_signature_builder=build_case_signature,
        workers=workers,
        logfn=logfn,
        progress_cb=progress_cb,
        cancel_cb=cancel_cb,
        flush_every_cases=flush_every_cases,
        chunk_cb=chunk_cb,
    )


__all__ = ("build_case_signature", "run_case", "run_cases")
