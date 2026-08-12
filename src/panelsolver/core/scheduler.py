"""Spawn-based, cache-aware scheduling for model-neutral case execution."""

from __future__ import annotations

import multiprocessing as mp
import os
import queue
import time
import traceback
from collections import OrderedDict, deque
from collections.abc import Callable, Hashable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .errors import PanelSolverError
from .execution import CaseExecutionRequest, CaseExecutionResult, execute_case

_DEFAULT_CHUNK_CASES = 8
_POLL_SECONDS = 0.1
_CLEANUP_SECONDS = 2.0


class SchedulerError(PanelSolverError, RuntimeError):
    """The shared scheduler could not complete its requested cases."""


class SchedulerCancelled(SchedulerError):
    """Cooperative cancellation stopped dispatch at a case boundary."""


class WorkerStartupError(SchedulerError):
    """A spawn worker could not be started."""


class WorkerExecutionError(SchedulerError):
    """A worker reported an exception with its remote traceback."""

    def __init__(
        self,
        worker_id: int,
        remote_error: str,
        remote_traceback: str,
    ) -> None:
        self.worker_id = worker_id
        self.remote_error = remote_error
        self.remote_traceback = remote_traceback
        detail = f"[WorkerError] worker {worker_id}: {remote_error}"
        if remote_traceback:
            detail = f"{detail}\n{remote_traceback}"
        super().__init__(detail)


class WorkerUnexpectedExitError(SchedulerError):
    """One or more busy workers exited without returning a message."""

    def __init__(self, exits: Sequence[tuple[int, int | None]]) -> None:
        self.exits = tuple((int(worker_id), exitcode) for worker_id, exitcode in exits)
        detail = ", ".join(
            f"worker {worker_id} (exit code {exitcode})"
            for worker_id, exitcode in self.exits
        )
        super().__init__(f"[WorkerError] {detail} exited without returning a result.")


class WorkerLogPolicy(str, Enum):
    """Explicit preservation of the D015 dual logging contracts."""

    FORWARD = "forward"
    DROP = "drop"


class PartialResultPolicy(str, Enum):
    """Explicit preservation of legacy worker-failure partial-result behavior."""

    YIELD_COMPLETED = "yield_completed"
    DISCARD_CHUNK = "discard_chunk"


@dataclass(frozen=True, slots=True)
class SchedulerProgress:
    """Deterministic completion count emitted for one successful case."""

    case_index: int
    completed: int
    total: int


def _positive_integer(value: object, *, field: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise SchedulerError(f"{field} must be an integer >= 1.")
    try:
        if isinstance(value, (str, int, np.integer)):
            parsed = int(value)
        else:
            raise TypeError
    except (TypeError, ValueError, OverflowError) as exc:
        raise SchedulerError(f"{field} must be an integer >= 1.") from exc
    if parsed < 1:
        raise SchedulerError(f"{field} must be an integer >= 1.")
    return parsed


def resolve_parallel_chunk_cases(
    chunk_cases: int | None = None,
    *,
    legacy_env_prefix: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Resolve explicit > neutral env > selected legacy env > default 8."""
    if legacy_env_prefix not in {None, "FMFSOLVER", "NEWTSOLVER"}:
        raise SchedulerError(
            "legacy_env_prefix must be None, 'FMFSOLVER', or 'NEWTSOLVER'."
        )
    if chunk_cases is not None:
        return _positive_integer(chunk_cases, field="chunk_cases")

    values = os.environ if environment is None else environment
    names = ["PANELSOLVER_PARALLEL_CHUNK_CASES"]
    if legacy_env_prefix is not None:
        names.append(f"{legacy_env_prefix}_PARALLEL_CHUNK_CASES")
    for name in names:
        raw = str(values.get(name, "")).strip()
        if raw:
            try:
                return _positive_integer(raw, field=name)
            except SchedulerError as exc:
                raise SchedulerError(f"{name} must be an integer >= 1.") from exc
    return _DEFAULT_CHUNK_CASES


def case_execution_bucket_keys(
    requests: Sequence[CaseExecutionRequest],
) -> tuple[Hashable, ...]:
    """Build scheduling hints without weakening any numerical cache identity."""
    keys: list[Hashable] = []
    for index, request in enumerate(requests):
        if not isinstance(request, CaseExecutionRequest):
            raise TypeError("requests must contain only CaseExecutionRequest instances")
        config = request.shielding
        if not config.enabled:
            keys.append(("single", index))
            continue
        keys.append(
            (
                "shield",
                request.stl_paths,
                request.scale_m_per_unit,
                request.mesh_validation_policy.value,
                tuple(float(value) for value in request.velocity_hat_stl),
                config.ray_backend.value,
                config.batch_size,
                config.cache_max,
                config.legacy_env_prefix,
            )
        )
    return tuple(keys)


def ordered_success_snapshot[ResultT](
    completed: Mapping[int, ResultT],
    execution_order: Sequence[int],
) -> tuple[tuple[int, ResultT], ...]:
    """Return checkpoint-ready successful results in caller-defined input order."""
    return tuple(
        (int(index), completed[int(index)])
        for index in execution_order
        if int(index) in completed
    )


def _validated_execution_order(total: int, order: Sequence[int] | None) -> tuple[int, ...]:
    raw = tuple(range(total)) if order is None else tuple(order)
    normalized: list[int] = []
    for value in raw:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise SchedulerError("execution_order must contain integer indices.")
        index = int(value)
        if index < 0 or index >= total:
            raise SchedulerError("execution_order contains an out-of-range index.")
        normalized.append(index)
    if len(normalized) != total or len(set(normalized)) != total:
        raise SchedulerError("execution_order must contain every case index exactly once.")
    return tuple(normalized)


def _validated_bucket_keys(
    total: int,
    bucket_keys: Sequence[Hashable] | None,
) -> tuple[Hashable, ...]:
    keys: tuple[Hashable, ...]
    if bucket_keys is None:
        keys = tuple(("single", index) for index in range(total))
    else:
        keys = tuple(bucket_keys)
    if len(keys) != total:
        raise SchedulerError("bucket_keys must have one entry per case.")
    try:
        for key in keys:
            hash(key)
    except TypeError as exc:
        raise SchedulerError("bucket_keys entries must be hashable.") from exc
    return keys


def _build_bucket_chunks(
    execution_order: Sequence[int],
    bucket_keys: Sequence[Hashable],
    chunk_cases: int,
) -> tuple[
    dict[Hashable, deque[tuple[int, ...]]],
    dict[Hashable, int],
]:
    buckets: OrderedDict[Hashable, list[int]] = OrderedDict()
    for index in execution_order:
        buckets.setdefault(bucket_keys[index], []).append(index)

    chunks: dict[Hashable, deque[tuple[int, ...]]] = {}
    remaining: dict[Hashable, int] = {}
    for key, indices in buckets.items():
        chunks[key] = deque(
            tuple(indices[start : start + chunk_cases])
            for start in range(0, len(indices), chunk_cases)
        )
        remaining[key] = len(indices)
    return chunks, remaining


def _pick_next_chunk(
    worker_id: int,
    worker_last_bucket: list[Hashable | None],
    bucket_chunks: dict[Hashable, deque[tuple[int, ...]]],
    bucket_remaining: dict[Hashable, int],
    bucket_owner: dict[Hashable, int | None],
) -> tuple[Hashable, tuple[int, ...]] | None:
    last = worker_last_bucket[worker_id]
    if last is not None and bucket_chunks.get(last):
        bucket = last
    else:
        unowned = [
            key
            for key, chunks in bucket_chunks.items()
            if chunks and bucket_owner.get(key) is None
        ]
        if unowned:
            bucket = max(unowned, key=lambda key: bucket_remaining[key])
            bucket_owner[bucket] = worker_id
        elif bucket_chunks:
            bucket = max(bucket_chunks, key=lambda key: bucket_remaining[key])
        else:
            return None
        worker_last_bucket[worker_id] = bucket

    indices = bucket_chunks[bucket].popleft()
    bucket_remaining[bucket] -= len(indices)
    if bucket_remaining[bucket] == 0:
        bucket_chunks.pop(bucket)
        bucket_remaining.pop(bucket)
        bucket_owner.pop(bucket, None)
    return bucket, indices


def _null_log(_message: str) -> None:
    return None


def _worker_loop[CaseT, ResultT](
    worker_id: int,
    task_queue: object,
    result_queue: object,
    cancel_event: object,
    run_case_fn: Callable[[CaseT, Callable[[str], None]], ResultT],
    capture_logs: bool,
    include_partial_results: bool,
) -> None:
    """Execute complete cases; cancellation is observed only between cases."""
    while True:
        message = task_queue.get()
        message_type = message.get("type")
        if message_type == "shutdown":
            return
        if message_type != "run_chunk":
            result_queue.put(
                {
                    "type": "error",
                    "worker_id": worker_id,
                    "error": f"Unknown task type: {message_type}",
                    "traceback": "",
                    "logs": (),
                    "results": (),
                }
            )
            return

        bucket = message.get("bucket")
        indices = tuple(message.get("indices") or ())
        cases = tuple(message.get("cases") or ())
        if len(indices) != len(cases):
            result_queue.put(
                {
                    "type": "error",
                    "worker_id": worker_id,
                    "bucket": bucket,
                    "error": "Task indices/cases size mismatch.",
                    "traceback": "",
                    "logs": (),
                    "results": (),
                }
            )
            return

        results: list[tuple[int, ResultT]] = []
        logs: list[str] = []
        logfn = logs.append if capture_logs else _null_log
        try:
            for index, case in zip(indices, cases, strict=True):
                if cancel_event.is_set():
                    break
                results.append((int(index), run_case_fn(case, logfn)))
        except Exception as exc:
            result_queue.put(
                {
                    "type": "error",
                    "worker_id": worker_id,
                    "bucket": bucket,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "logs": tuple(logs),
                    "results": tuple(results) if include_partial_results else (),
                }
            )
            return

        result_queue.put(
            {
                "type": "chunk_done",
                "worker_id": worker_id,
                "bucket": bucket,
                "canceled": bool(cancel_event.is_set()),
                "logs": tuple(logs),
                "results": tuple(results),
            }
        )


def _cleanup_workers(
    cancel_event: object,
    task_queues: Sequence[object],
    started_processes: Sequence[mp.Process],
) -> None:
    cancel_event.set()
    for task_queue in task_queues:
        try:
            task_queue.put({"type": "shutdown"}, block=False)
        except Exception:
            pass

    deadline = time.monotonic() + _CLEANUP_SECONDS
    for process in started_processes:
        process.join(timeout=max(0.0, deadline - time.monotonic()))
    for process in started_processes:
        if process.is_alive():
            process.terminate()
    deadline = time.monotonic() + _CLEANUP_SECONDS
    for process in started_processes:
        if process.is_alive():
            process.join(timeout=max(0.0, deadline - time.monotonic()))
    for task_queue in task_queues:
        try:
            task_queue.cancel_join_thread()
            task_queue.close()
        except Exception:
            pass


def iter_case_results_parallel[CaseT, ResultT](
    cases: Sequence[CaseT],
    workers: int,
    run_case_fn: Callable[[CaseT, Callable[[str], None]], ResultT],
    *,
    log_policy: WorkerLogPolicy | str,
    partial_result_policy: PartialResultPolicy | str,
    execution_order: Sequence[int] | None = None,
    bucket_keys: Sequence[Hashable] | None = None,
    chunk_cases: int | None = None,
    legacy_env_prefix: str | None = None,
    cancel_cb: Callable[[], bool] | None = None,
    logfn: Callable[[str], None] | None = None,
    progress_cb: Callable[[SchedulerProgress], None] | None = None,
    snapshot_cb: Callable[[tuple[tuple[int, ResultT], ...]], None] | None = None,
) -> Iterator[tuple[int, ResultT]]:
    """Yield completion-order results from spawn workers.

    Final and checkpoint order is recovered with ``ordered_success_snapshot``.
    The two legacy log and failure-partial behaviors are required policy inputs,
    not silently normalized defaults.
    """
    records = tuple(cases)
    total = len(records)
    if total == 0:
        return
    worker_count = _positive_integer(workers, field="workers")
    if worker_count < 2 or total < 2:
        raise SchedulerError(
            "iter_case_results_parallel requires workers >= 2 and at least 2 cases."
        )
    worker_count = min(worker_count, total)
    if not callable(run_case_fn):
        raise TypeError("run_case_fn must be callable")
    try:
        selected_log_policy = WorkerLogPolicy(log_policy)
    except (TypeError, ValueError) as exc:
        raise SchedulerError("log_policy must be 'forward' or 'drop'.") from exc
    try:
        selected_partial_policy = PartialResultPolicy(partial_result_policy)
    except (TypeError, ValueError) as exc:
        raise SchedulerError(
            "partial_result_policy must be 'yield_completed' or 'discard_chunk'."
        ) from exc

    order = _validated_execution_order(total, execution_order)
    keys = _validated_bucket_keys(total, bucket_keys)
    resolved_chunk_cases = resolve_parallel_chunk_cases(
        chunk_cases,
        legacy_env_prefix=legacy_env_prefix,
    )
    bucket_chunks, bucket_remaining = _build_bucket_chunks(
        order,
        keys,
        resolved_chunk_cases,
    )
    bucket_owner: dict[Hashable, int | None] = {
        bucket: None for bucket in bucket_chunks
    }
    worker_last_bucket: list[Hashable | None] = [None] * worker_count

    context = mp.get_context("spawn")
    cancel_event = context.Event()
    task_queues = [context.Queue(maxsize=1) for _ in range(worker_count)]
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_worker_loop,
            args=(
                worker_id,
                task_queues[worker_id],
                result_queue,
                cancel_event,
                run_case_fn,
                selected_log_policy is WorkerLogPolicy.FORWARD,
                selected_partial_policy is PartialResultPolicy.YIELD_COMPLETED,
            ),
            daemon=True,
        )
        for worker_id in range(worker_count)
    ]
    worker_busy = [False] * worker_count
    started_processes: list[mp.Process] = []
    completed: dict[int, ResultT] = {}
    cancellation_requested = False

    def assign_next(worker_id: int) -> bool:
        picked = _pick_next_chunk(
            worker_id,
            worker_last_bucket,
            bucket_chunks,
            bucket_remaining,
            bucket_owner,
        )
        if picked is None:
            return False
        bucket, indices = picked
        task_queues[worker_id].put(
            {
                "type": "run_chunk",
                "bucket": bucket,
                "indices": indices,
                "cases": tuple(records[index] for index in indices),
            }
        )
        worker_busy[worker_id] = True
        return True

    def accept_result(index: int, result: ResultT) -> tuple[int, ResultT]:
        if index in completed:
            raise SchedulerError(f"worker returned duplicate case index {index}.")
        completed[index] = result
        if progress_cb is not None:
            progress_cb(SchedulerProgress(index, len(completed), total))
        if snapshot_cb is not None:
            snapshot_cb(ordered_success_snapshot(completed, order))
        return index, result

    try:
        try:
            for process in processes:
                process.start()
                started_processes.append(process)
        except Exception as exc:
            raise WorkerStartupError(f"Could not start spawn worker: {exc}") from exc

        for worker_id in range(worker_count):
            assign_next(worker_id)

        while len(completed) < total:
            if (
                not cancellation_requested
                and cancel_cb is not None
                and bool(cancel_cb())
            ):
                cancellation_requested = True
                cancel_event.set()
            if cancellation_requested and not any(worker_busy):
                raise SchedulerCancelled("Canceled by user at a case boundary.")

            try:
                message = result_queue.get(timeout=_POLL_SECONDS)
            except queue.Empty:
                dead_workers = [
                    (worker_id, processes[worker_id].exitcode)
                    for worker_id in range(worker_count)
                    if worker_busy[worker_id]
                    and not processes[worker_id].is_alive()
                ]
                if dead_workers:
                    cancel_event.set()
                    raise WorkerUnexpectedExitError(dead_workers)
                continue

            worker_id = int(message.get("worker_id", -1))
            if worker_id < 0 or worker_id >= worker_count:
                cancel_event.set()
                raise SchedulerError("worker returned an invalid worker_id.")
            worker_busy[worker_id] = False

            if selected_log_policy is WorkerLogPolicy.FORWARD and logfn is not None:
                for worker_message in message.get("logs") or ():
                    logfn(str(worker_message))

            message_type = message.get("type")
            if message_type == "error":
                cancel_event.set()
                if selected_partial_policy is PartialResultPolicy.YIELD_COMPLETED:
                    for index, result in message.get("results") or ():
                        yield accept_result(int(index), result)
                raise WorkerExecutionError(
                    worker_id,
                    str(message.get("error") or "Unknown worker error."),
                    str(message.get("traceback") or ""),
                )
            if message_type != "chunk_done":
                cancel_event.set()
                raise SchedulerError(
                    f"worker returned unknown message type: {message_type!r}."
                )

            bucket = message.get("bucket")
            if bucket is not None:
                worker_last_bucket[worker_id] = bucket
            if bool(message.get("canceled")):
                cancellation_requested = True
                cancel_event.set()
            for index, result in message.get("results") or ():
                yield accept_result(int(index), result)

            if not cancellation_requested and len(completed) < total:
                assign_next(worker_id)

        if cancellation_requested:
            raise SchedulerCancelled("Canceled by user at a case boundary.")
    finally:
        _cleanup_workers(cancel_event, task_queues, started_processes)
        try:
            result_queue.cancel_join_thread()
            result_queue.close()
        except Exception:
            pass


def _execute_request_worker(
    request: CaseExecutionRequest,
    logfn: Callable[[str], None],
) -> CaseExecutionResult:
    return execute_case(request, warning_callback=logfn)


def iter_execution_results_parallel(
    requests: Sequence[CaseExecutionRequest],
    workers: int,
    *,
    log_policy: WorkerLogPolicy | str,
    partial_result_policy: PartialResultPolicy | str,
    execution_order: Sequence[int] | None = None,
    chunk_cases: int | None = None,
    legacy_env_prefix: str | None = None,
    cancel_cb: Callable[[], bool] | None = None,
    logfn: Callable[[str], None] | None = None,
    progress_cb: Callable[[SchedulerProgress], None] | None = None,
    snapshot_cb: Callable[
        [tuple[tuple[int, CaseExecutionResult], ...]],
        None,
    ]
    | None = None,
) -> Iterator[tuple[int, CaseExecutionResult]]:
    """Run Phase 5 requests through the same one-case engine in spawn workers."""
    normalized = tuple(requests)
    yield from iter_case_results_parallel(
        normalized,
        workers,
        _execute_request_worker,
        log_policy=log_policy,
        partial_result_policy=partial_result_policy,
        execution_order=execution_order,
        bucket_keys=case_execution_bucket_keys(normalized),
        chunk_cases=chunk_cases,
        legacy_env_prefix=legacy_env_prefix,
        cancel_cb=cancel_cb,
        logfn=logfn,
        progress_cb=progress_cb,
        snapshot_cb=snapshot_cb,
    )


__all__ = (
    "PartialResultPolicy",
    "SchedulerCancelled",
    "SchedulerError",
    "SchedulerProgress",
    "WorkerExecutionError",
    "WorkerLogPolicy",
    "WorkerStartupError",
    "WorkerUnexpectedExitError",
    "case_execution_bucket_keys",
    "iter_case_results_parallel",
    "iter_execution_results_parallel",
    "ordered_success_snapshot",
    "resolve_parallel_chunk_cases",
)
