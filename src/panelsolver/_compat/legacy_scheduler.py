"""Frozen DataFrame scheduler signatures over the shared worker engine."""

from __future__ import annotations

import queue
from collections.abc import Callable, Iterator

import pandas as pd

from panelsolver.app.attitude import resolve_attitude
from panelsolver.app.environment import resolve_parallel_chunk_environment
from panelsolver.core import (
    PartialResultPolicy,
    SchedulerCancelled,
    SchedulerError,
    WorkerExecutionError,
    WorkerLogPolicy,
    WorkerStartupError,
    WorkerUnexpectedExitError,
    iter_case_results_parallel,
)


class _LegacyCallbackError(BaseException):
    """Carry one callback-owned exception through shared runtime handling."""

    def __init__(self, error: BaseException) -> None:
        self.error = error
        super().__init__()


def _callback_error(exc: _LegacyCallbackError) -> BaseException:
    for note in getattr(exc, "__notes__", ()):
        exc.error.add_note(note)
    return exc.error


def resolve_legacy_parallel_chunk_cases(legacy_env_prefix: str) -> int:
    """Resolve the product's frozen environment variable and default."""
    return resolve_parallel_chunk_environment(
        legacy_env_prefix=legacy_env_prefix,
    )


def legacy_cancel_callback(
    cancel_cb: Callable[[], bool] | None,
) -> Callable[[], bool] | None:
    """Restore the frozen immediate-cancellation callback contract."""
    if cancel_cb is None:
        return None

    def wrapped() -> bool:
        try:
            requested = bool(cancel_cb())
        except BaseException as exc:
            raise _LegacyCallbackError(exc) from None
        if requested:
            raise RuntimeError("Canceled by user.")
        return False

    return wrapped


def legacy_callback[ReturnT](
    callback: Callable[..., ReturnT] | None,
) -> Callable[..., ReturnT] | None:
    """Tag callback-owned exceptions so runtime errors alone are translated."""
    if callback is None:
        return None

    def wrapped(*args, **kwargs) -> ReturnT:
        try:
            return callback(*args, **kwargs)
        except BaseException as exc:
            raise _LegacyCallbackError(exc) from None

    return wrapped


def _legacy_log_callback(callback) -> Callable[..., object]:
    """Defer the frozen required-log callback check until a message is emitted."""

    def wrapped(*args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except BaseException as exc:
            raise _LegacyCallbackError(exc) from None

    return wrapped


def _legacy_remote_error(exc: WorkerExecutionError) -> str:
    remote_error = exc.remote_error
    if remote_error.startswith("Unable to read mesh source "):
        marker = "FileNotFoundError: "
        for line in exc.remote_traceback.splitlines():
            stripped = line.strip()
            if stripped.startswith(marker):
                return stripped.removeprefix(marker)
    return remote_error


def _preserve_scheduler_notes(
    translated: BaseException,
    source: SchedulerError,
) -> BaseException:
    for note in getattr(source, "__notes__", ()):
        translated.add_note(note)
    return translated


def _restore_unexpected_exit_context(
    translated: RuntimeError,
    source: WorkerUnexpectedExitError,
) -> RuntimeError:
    """Reproduce polling context or retain a Phase 8 transport failure chain."""
    if source.__cause__ is not None or source.__context__ is not None:
        translated.__cause__ = source.__cause__
        translated.__context__ = source.__context__
        translated.__suppress_context__ = source.__suppress_context__
        return translated
    translated.__cause__ = None
    translated.__context__ = queue.Empty()
    translated.__suppress_context__ = False
    return translated


def translate_legacy_scheduler_error(
    exc: SchedulerError,
    *,
    legacy_env_prefix: str,
) -> BaseException:
    """Translate shared scheduler failures at a frozen Python boundary."""
    strict = legacy_env_prefix == "FMFSOLVER"
    if isinstance(exc, SchedulerCancelled):
        translated: BaseException = RuntimeError("Canceled by user.")
        return _preserve_scheduler_notes(translated, exc)
    if isinstance(exc, WorkerExecutionError):
        detail = f"[WorkerError] {_legacy_remote_error(exc)}"
        if exc.remote_traceback:
            detail = f"{detail}\n{exc.remote_traceback}"
        translated = RuntimeError(detail)
        return _preserve_scheduler_notes(translated, exc)
    if isinstance(exc, WorkerUnexpectedExitError):
        if strict:
            details = ", ".join(
                f"worker {worker_id} exitcode={exitcode}"
                for worker_id, exitcode in exc.exits
            )
        else:
            details = ", ".join(
                f"worker {worker_id} (exit code {exitcode})"
                for worker_id, exitcode in exc.exits
            )
            translated = RuntimeError(
                f"[WorkerError] {details} exited without returning a result."
            )
            translated = _restore_unexpected_exit_context(translated, exc)
            return _preserve_scheduler_notes(translated, exc)
        translated = RuntimeError(
            f"[WorkerError] Worker exited unexpectedly: {details}"
        )
        translated = _restore_unexpected_exit_context(translated, exc)
        return _preserve_scheduler_notes(translated, exc)
    if (
        isinstance(exc, WorkerStartupError)
        and exc.__cause__ is not None
        and str(exc).startswith(
            (
                "Could not serialize spawn worker callable:",
                "Could not start spawn worker:",
            )
        )
    ):
        return _preserve_scheduler_notes(exc.__cause__, exc)
    translated = RuntimeError(str(exc))
    if isinstance(exc, WorkerStartupError):
        translated.__cause__ = exc.__cause__
        translated.__context__ = exc.__context__
        translated.__suppress_context__ = exc.__suppress_context__
    return _preserve_scheduler_notes(translated, exc)


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
    translated_error: BaseException | None = None
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
            chunk_cases=resolve_parallel_chunk_environment(
                chunk_cases,
                legacy_env_prefix=legacy_env_prefix,
            ),
            cancel_cb=legacy_cancel_callback(cancel_cb),
            logfn=legacy_callback(logfn),
        )
    except _LegacyCallbackError as exc:
        translated_error = _callback_error(exc)
    except SchedulerError as exc:
        translated_error = translate_legacy_scheduler_error(
            exc,
            legacy_env_prefix=legacy_env_prefix,
        )
    if translated_error is not None:
        raise translated_error


__all__ = (
    "iter_legacy_case_results_parallel",
    "legacy_execution_order",
    "resolve_legacy_parallel_chunk_cases",
)
