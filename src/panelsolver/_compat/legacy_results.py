"""DataFrame and direct-result adapters for frozen Python callers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pandas as pd

from panelsolver.app.csv_writer import (
    CSV_ENCODING,
    AtomicCsvWritePolicy,
    write_csv_atomic,
)
from panelsolver.app.runtime import (
    DEFAULT_CHECKPOINT_CASES,
    ProductBatchRunResult,
    ProductRuntimePolicy,
    _maybe_log_ray_accel_hint,
    _run_product_case_without_orchestration,
)
from panelsolver.core import CsvProjection, MeshLoadError, SchedulerError

from .legacy_scheduler import (
    _callback_error,
    _legacy_log_callback,
    _LegacyCallbackError,
    legacy_callback,
    legacy_cancel_callback,
    translate_legacy_scheduler_error,
)

_LEGACY_COMPONENT_RESULT_COLUMNS = (
    "scope",
    "component_id",
    "component_stl_path",
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
)


def legacy_result_frame(
    projection: CsvProjection,
    *,
    input_columns: Sequence[str],
    renames: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Strip merged input columns and restore direct-result legacy names."""
    rows: list[dict[str, object]] = []
    for row in projection.rows:
        normalized = dict(row)
        if row.get("scope") == "total":
            for name in ("component_id", "component_stl_path"):
                if name in normalized:
                    normalized[name] = ""
            for name in ("vtp_path",):
                if name in normalized and normalized[name] is None:
                    normalized[name] = ""
        elif row.get("scope") == "component":
            if "component_id" in normalized:
                normalized["component_id"] = int(normalized["component_id"])
            for name in ("vtp_path",):
                if name in normalized:
                    normalized[name] = ""
        rows.append(normalized)
    frame = pd.DataFrame(rows, columns=projection.columns)
    retained = [
        name
        for name in projection.columns
        if name == "case_id" or name not in set(input_columns)
    ]
    return frame[retained].rename(columns=dict(renames or {}))


def run_legacy_cases(
    frame: pd.DataFrame,
    runtime_run_cases: Callable[..., ProductBatchRunResult],
    *,
    legacy_env_prefix: str,
    input_columns: Sequence[str],
    renames: Mapping[str, str] | None = None,
    legacy_signature_builder=None,
    runtime_policy: ProductRuntimePolicy | None = None,
    workers: int = 1,
    logfn=None,
    progress_cb=None,
    cancel_cb=None,
    checkpoint_every_cases: int | None = DEFAULT_CHECKPOINT_CASES,
    chunk_cb=None,
) -> pd.DataFrame:
    """Run shared execution and retain the frozen DataFrame callback shape."""
    compat_cancel_cb = legacy_cancel_callback(cancel_cb)
    if frame.empty:
        checkpoint_every = int(checkpoint_every_cases or 0)
        if checkpoint_every < 0:
            raise ValueError("checkpoint_every_cases must be >= 0.")
        callback_error: BaseException | None = None
        try:
            if compat_cancel_cb is not None:
                compat_cancel_cb()
        except _LegacyCallbackError as exc:
            callback_error = _callback_error(exc)
        if callback_error is not None:
            raise callback_error
        if runtime_policy is not None:
            hint_error: BaseException | None = None
            try:
                _maybe_log_ray_accel_hint(
                    runtime_policy,
                    _legacy_log_callback(logfn),
                )
            except _LegacyCallbackError as exc:
                hint_error = _callback_error(exc)
            if hint_error is not None:
                raise hint_error
        return pd.DataFrame()
    compat_logfn = _legacy_log_callback(logfn)
    compat_progress_cb = legacy_callback(progress_cb)
    compat_chunk_cb = legacy_callback(chunk_cb)
    direct_input_columns = tuple(
        dict.fromkeys((*input_columns, *(str(name) for name in frame.columns)))
    )

    def converted(projection: CsvProjection) -> pd.DataFrame:
        result_frame = legacy_result_frame(
            projection,
            input_columns=direct_input_columns,
            renames=renames,
        )
        if legacy_signature_builder is None or "case_signature" not in result_frame:
            return result_frame
        source_rows = frame.to_dict(orient="records")
        unused = list(range(len(source_rows)))
        total_positions = result_frame.index[result_frame["scope"] == "total"].tolist()
        for block_index, start in enumerate(total_positions):
            case_id = str(result_frame.at[start, "case_id"])
            source_index = next(
                index
                for index in unused
                if str(source_rows[index].get("case_id")) == case_id
            )
            unused.remove(source_index)
            stop = (
                total_positions[block_index + 1]
                if block_index + 1 < len(total_positions)
                else len(result_frame)
            )
            result_frame.loc[start : stop - 1, "case_signature"] = (
                legacy_signature_builder(source_rows[source_index])
            )
        return result_frame

    def snapshot(projection, done: int, total: int, final: bool) -> None:
        if compat_chunk_cb is not None:
            compat_chunk_cb(
                converted(projection),
                done,
                total,
                final,
            )

    translated_error: BaseException | None = None
    try:
        result = runtime_run_cases(
            frame.to_dict(orient="records"),
            workers=workers,
            logfn=compat_logfn,
            progress_cb=compat_progress_cb,
            cancel_cb=compat_cancel_cb,
            checkpoint_every_cases=checkpoint_every_cases,
            snapshot_cb=snapshot if compat_chunk_cb is not None else None,
        )
    except _LegacyCallbackError as exc:
        translated_error = _callback_error(exc)
    except MeshLoadError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            translated_error = exc.__cause__
        else:
            raise
    except SchedulerError as exc:
        translated_error = translate_legacy_scheduler_error(
            exc,
            legacy_env_prefix=legacy_env_prefix,
        )
    if translated_error is not None:
        raise translated_error
    return converted(result.csv)


def run_legacy_case(
    row: Mapping[str, object],
    runtime_policy: ProductRuntimePolicy,
    *,
    legacy_env_prefix: str,
    input_columns: Sequence[str],
    renames: Mapping[str, str] | None = None,
    legacy_signature_builder=None,
    logfn=None,
) -> dict[str, object]:
    """Run one frozen direct case without batch-orchestration logging."""

    def runtime_run_case(rows, **runtime_kwargs) -> ProductBatchRunResult:
        if len(rows) != 1:
            raise RuntimeError("direct legacy execution requires exactly one row")
        result = _run_product_case_without_orchestration(
            rows[0],
            runtime_policy,
            logfn=runtime_kwargs["logfn"],
        )
        return ProductBatchRunResult((result,), result.csv)

    frame = run_legacy_cases(
        pd.DataFrame([dict(row)]),
        runtime_run_case,
        legacy_env_prefix=legacy_env_prefix,
        input_columns=input_columns,
        renames=renames,
        legacy_signature_builder=legacy_signature_builder,
        runtime_policy=runtime_policy,
        logfn=logfn,
    )
    return direct_legacy_result(frame)


def direct_legacy_result(frame: pd.DataFrame) -> dict[str, object]:
    """Collapse one total/component result frame to the legacy dictionary."""
    total = frame.loc[frame["scope"] == "total"].iloc[0].to_dict()
    component_rows = frame.loc[
        frame["scope"] == "component",
        list(_LEGACY_COMPONENT_RESULT_COLUMNS),
    ].to_dict(orient="records")
    total["component_rows"] = component_rows
    return total


def merge_legacy_result_frames(
    input_frame: pd.DataFrame,
    result_frame: pd.DataFrame,
    *,
    input_column_order: Sequence[str],
) -> pd.DataFrame:
    """Preserve frozen input-first columns and total/component ordering."""
    inputs = input_frame.reset_index(drop=True).copy()
    ordered = [name for name in input_column_order if name in inputs.columns]
    ordered.extend(name for name in inputs.columns if name not in ordered)
    inputs = inputs[ordered]
    if "case_id" in inputs:
        inputs["case_id"] = inputs["case_id"].astype(str)
    results = result_frame.reset_index(drop=True).copy()
    if "case_id" in results:
        results["case_id"] = results["case_id"].astype(str)
    overlaps = [
        name for name in results.columns if name in inputs.columns and name != "case_id"
    ]
    if overlaps:
        results.rename(columns={name: f"out_{name}" for name in overlaps}, inplace=True)
    if "case_id" not in results or "case_id" not in inputs:
        return pd.concat([inputs, results], axis=1)
    combined = results.merge(inputs, on="case_id", how="left", sort=False)
    output_columns = [name for name in combined.columns if name not in ordered]
    combined = combined[ordered + output_columns]
    case_order = {
        case_id: index for index, case_id in enumerate(inputs["case_id"].tolist())
    }
    combined["_case_order"] = (
        combined["case_id"].map(case_order).fillna(len(case_order)).astype(int)
    )
    combined["_scope_order"] = (
        combined["scope"].map({"total": 0, "component": 1}).fillna(2)
        if "scope" in combined
        else 0
    )
    combined["_component_order"] = (
        pd.to_numeric(combined["component_id"], errors="coerce")
        .fillna(-1)
        .astype(int)
        if "component_id" in combined
        else -1
    )
    return combined.sort_values(
        ["_case_order", "_scope_order", "_component_order"], kind="mergesort"
    ).drop(columns=["_case_order", "_scope_order", "_component_order"])


def write_legacy_results_csv(
    out_path: str | Path,
    input_frame: pd.DataFrame,
    result_frame: pd.DataFrame,
    *,
    input_column_order: Sequence[str],
    policy: AtomicCsvWritePolicy,
) -> None:
    """Use the shared atomic writer for an arbitrary frozen result frame."""
    combined = merge_legacy_result_frames(
        input_frame,
        result_frame,
        input_column_order=input_column_order,
    )
    projection = CsvProjection(
        tuple(combined.columns),
        tuple(combined.where(pd.notna(combined), None).to_dict(orient="records")),
    )
    write_csv_atomic(out_path, projection, policy)


def append_legacy_results_csv(
    out_path: str | Path,
    input_frame: pd.DataFrame,
    result_frame: pd.DataFrame,
    *,
    input_column_order: Sequence[str],
) -> None:
    """Retain the frozen append behavior for existing summary files."""
    if result_frame is None or result_frame.empty:
        return
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined = merge_legacy_result_frames(
        input_frame,
        result_frame,
        input_column_order=input_column_order,
    )
    write_header = not output.exists() or output.stat().st_size == 0
    combined.to_csv(
        output,
        mode="w" if write_header else "a",
        header=write_header,
        index=False,
        encoding=CSV_ENCODING,
    )


__all__ = (
    "append_legacy_results_csv",
    "direct_legacy_result",
    "legacy_result_frame",
    "merge_legacy_result_frames",
    "run_legacy_cases",
    "write_legacy_results_csv",
)
