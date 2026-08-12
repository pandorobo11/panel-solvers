"""DataFrame and direct-result adapters for frozen Python callers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pandas as pd

from panelsolver.core import CsvProjection

from .csv_writer import AtomicCsvWritePolicy, write_csv_atomic
from .runtime import ProductBatchRunResult

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
    "npz_path",
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
            for name in ("vtp_path", "npz_path"):
                if name in normalized and normalized[name] is None:
                    normalized[name] = ""
        elif row.get("scope") == "component":
            if "component_id" in normalized:
                normalized["component_id"] = int(normalized["component_id"])
            for name in ("vtp_path", "npz_path"):
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
    input_columns: Sequence[str],
    renames: Mapping[str, str] | None = None,
    legacy_signature_builder=None,
    workers: int = 1,
    logfn=None,
    progress_cb=None,
    cancel_cb=None,
    flush_every_cases: int | None = None,
    chunk_cb=None,
) -> pd.DataFrame:
    """Run shared execution and retain the frozen DataFrame callback shape."""
    if frame.empty:
        return pd.DataFrame()
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
        if chunk_cb is not None:
            chunk_cb(
                converted(projection),
                done,
                total,
                final,
            )

    result = runtime_run_cases(
        frame.to_dict(orient="records"),
        workers=workers,
        logfn=logfn,
        progress_cb=progress_cb,
        cancel_cb=cancel_cb,
        flush_every_cases=flush_every_cases,
        snapshot_cb=snapshot if chunk_cb is not None else None,
    )
    return converted(result.csv)


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
    )


__all__ = (
    "append_legacy_results_csv",
    "direct_legacy_result",
    "legacy_result_frame",
    "merge_legacy_result_frames",
    "run_legacy_cases",
    "write_legacy_results_csv",
)
