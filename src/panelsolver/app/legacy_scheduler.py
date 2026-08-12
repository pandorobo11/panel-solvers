"""Frozen DataFrame scheduler signatures over the shared worker engine."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pandas as pd

from panelsolver.core import (
    PartialResultPolicy,
    SchedulerCancelled,
    WorkerExecutionError,
    WorkerLogPolicy,
    WorkerUnexpectedExitError,
    iter_case_results_parallel,
    resolve_parallel_chunk_cases,
)

from .attitude import resolve_attitude


def resolve_legacy_parallel_chunk_cases(legacy_env_prefix: str) -> int:
    """Resolve the product's frozen environment variable and default."""
    return resolve_parallel_chunk_cases(legacy_env_prefix=legacy_env_prefix)


def _bucket_key(row: dict[str, object], index: int, *, strict: bool) -> tuple:
    try:
        shielding_on = bool(int(row.get("shielding_on", 0)))
    except Exception:
        shielding_on = False
    if not shielding_on:
        return ("single", index)
    paths = tuple(
        token.strip()
        for token in str(row.get("stl_path", "")).split(";")
        if token.strip()
    )
    attitude = resolve_attitude(
        float(row.get("alpha_deg", 0.0)),
        float(row["beta_or_bank_deg"]),
        row.get("attitude_input"),
        strict_beta_tan_domain=strict,
    )
    return (
        "shield",
        paths,
        round(float(row.get("stl_scale_m_per_unit", 1.0)), 12),
        round(attitude.alpha_t_deg, 12),
        round(attitude.beta_t_deg, 12),
        str(row.get("ray_backend", "auto")).strip().lower() or "auto",
    )


def legacy_execution_order(frame: pd.DataFrame, *, strict: bool) -> list[int]:
    """Return the pinned shielding-first order without changing output order."""
    records = frame.to_dict(orient="records")

    def execution_key(index: int) -> tuple:
        bucket = _bucket_key(records[index], index, strict=strict)
        return (0, *bucket[1:], index) if bucket[0] == "shield" else (1, index)

    return sorted(range(len(records)), key=execution_key)


def iter_legacy_case_results_parallel(
    frame: pd.DataFrame,
    execution_order: list[int],
    workers: int,
    run_case_fn: Callable[[dict, Callable[[str], None]], dict],
    *,
    legacy_env_prefix: str,
    chunk_cases: int | None = None,
    cancel_cb: Callable[[], bool] | None = None,
    logfn: Callable[[str], None] | None = None,
) -> Iterator[tuple[int, dict]]:
    """Adapt records and explicit FMF/newtsolver worker policies."""
    records = tuple(frame.to_dict(orient="records"))
    strict = legacy_env_prefix == "FMFSOLVER"
    bucket_keys = tuple(
        _bucket_key(record, index, strict=strict)
        for index, record in enumerate(records)
    )
    try:
        yield from iter_case_results_parallel(
            records,
            workers,
            run_case_fn,
            log_policy=(WorkerLogPolicy.FORWARD if strict else WorkerLogPolicy.DROP),
            partial_result_policy=(
                PartialResultPolicy.DISCARD_CHUNK
                if strict
                else PartialResultPolicy.YIELD_COMPLETED
            ),
            execution_order=execution_order,
            bucket_keys=bucket_keys,
            chunk_cases=chunk_cases,
            legacy_env_prefix=legacy_env_prefix,
            cancel_cb=cancel_cb,
            logfn=logfn,
        )
    except SchedulerCancelled as exc:
        raise RuntimeError("Canceled by user.") from exc
    except WorkerExecutionError as exc:
        detail = f"[WorkerError] {exc.remote_error}"
        if exc.remote_traceback:
            detail = f"{detail}\n{exc.remote_traceback}"
        raise RuntimeError(detail) from exc
    except WorkerUnexpectedExitError as exc:
        if not strict:
            raise
        details = ", ".join(
            f"worker {worker_id} exitcode={exitcode}"
            for worker_id, exitcode in exc.exits
        )
        raise RuntimeError(
            f"[WorkerError] Worker exited unexpectedly: {details}"
        ) from exc


__all__ = (
    "iter_legacy_case_results_parallel",
    "legacy_execution_order",
    "resolve_legacy_parallel_chunk_cases",
)
