"""Thin newtsolver policies for shared execution, artifacts, and GUI adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from panelsolver.app import (
    GuiRunRequest,
    GuiRunResult,
    ProductBatchRunResult,
    ProductProjectionAdditions,
    ProductRuntimePolicy,
    SolverGuiAdapters,
    run_and_write_product_cases,
    run_product_cases,
)
from panelsolver.core import CaseExecutionResult, PartialResultPolicy, WorkerLogPolicy

from .case_adapter import CASE_POLICY, adapt_row, build_signatures
from .csv_adapter import (
    CSV_PROJECTION_POLICY,
    CSV_WRITE_POLICY,
    validate_results_output_path,
)
from .io.io_cases import read_cases


def _projection_additions(
    _row: Mapping[str, object],
    execution: CaseExecutionResult,
) -> ProductProjectionAdditions:
    metadata = execution.results.local_loads.metadata
    return ProductProjectionAdditions(
        vtp_field_data={
            "windward_eq_used": str(metadata["windward_eq"]),
            "leeward_eq_used": str(metadata["leeward_eq"]),
        }
    )


RUNTIME_POLICY = ProductRuntimePolicy(
    product_id="newtsolver",
    case_policy=CASE_POLICY,
    csv_projection_policy=CSV_PROJECTION_POLICY,
    csv_write_policy=CSV_WRITE_POLICY,
    worker_log_policy=WorkerLogPolicy.DROP,
    partial_result_policy=PartialResultPolicy.YIELD_COMPLETED,
    build_projection_additions=_projection_additions,
)


def run_cases(
    rows: Sequence[Mapping[str, object]],
    *,
    workers: int = 1,
    logfn=None,
    progress_cb=None,
    cancel_cb=None,
    flush_every_cases: int | None = None,
    snapshot_cb=None,
) -> ProductBatchRunResult:
    return run_product_cases(
        rows,
        RUNTIME_POLICY,
        workers=workers,
        logfn=logfn,
        progress_cb=progress_cb,
        cancel_cb=cancel_cb,
        flush_every_cases=flush_every_cases,
        snapshot_cb=snapshot_cb,
    )


def _read_gui_cases(path: str | Path) -> tuple[dict[str, object], ...]:
    return tuple(read_cases(path).to_dict(orient="records"))


def _validate_gui_output(
    output_path: str | Path,
    input_path: str | Path,
    rows: Sequence[Mapping[str, object]],
) -> Path:
    return validate_results_output_path(output_path, input_path, rows)


def _resolve_velocity(row: Mapping[str, object]):
    return adapt_row(row).attitude.velocity_hat_stl


def _run_gui_cases(request: GuiRunRequest) -> GuiRunResult:
    result = run_and_write_product_cases(
        request.rows,
        RUNTIME_POLICY,
        request.output_path,
        workers=request.workers,
        logfn=request.log,
        progress_cb=request.progress,
        cancel_cb=request.cancel_requested,
        flush_every_cases=100,
        log_snapshots=True,
    )
    first = result.cases[0]
    return GuiRunResult(
        first_vtp_path=first.vtp_path or None,
        first_case_row=request.rows[0] if first.vtp_path else None,
    )


GUI_ADAPTERS = SolverGuiAdapters(
    read_cases=_read_gui_cases,
    build_case_signatures=build_signatures,
    run_cases=_run_gui_cases,
    validate_output_path=_validate_gui_output,
    resolve_velocity_hat_stl=_resolve_velocity,
)


__all__ = ("GUI_ADAPTERS", "RUNTIME_POLICY", "run_cases")
