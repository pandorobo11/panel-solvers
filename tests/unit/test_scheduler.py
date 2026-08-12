from __future__ import annotations

import multiprocessing as mp
import os
import signal
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import panelsolver.core.scheduler as scheduler_module
from panelsolver.core import (
    PartialResultPolicy,
    SchedulerCancelled,
    SchedulerError,
    WorkerExecutionError,
    WorkerLogPolicy,
    WorkerStartupError,
    WorkerUnexpectedExitError,
    iter_case_results_parallel,
    ordered_success_snapshot,
    resolve_parallel_chunk_cases,
)


def _success_worker(case: tuple[int, float], logfn) -> int:
    value, delay_seconds = case
    time.sleep(delay_seconds)
    logfn(f"case={value}")
    return value * 10


def _failure_worker(case: int, logfn) -> int:
    logfn(f"case={case}")
    if case == 1:
        raise ValueError("deliberate worker failure")
    return case * 10


def _unexpected_exit_worker(case: int, _logfn) -> int:
    if case == 0:
        os._exit(7)
    time.sleep(0.3)
    return case


def _unpickleable_worker(case: str, logfn):
    if case == "result":
        return lambda: None
    if case == "log":
        logfn(lambda: None)
        return 1
    if case == "error":
        raise ValueError("failure after an unpickleable partial result")
    return 1


def _identity_worker(case, _logfn):
    return case


def _touch_after_delay(path_text: str) -> None:
    time.sleep(0.02)
    Path(path_text).touch()


def _large_result_worker(case: tuple[str, str, str], _logfn):
    behavior, ready_text, release_text = case
    ready = Path(ready_text)
    release = Path(release_text)
    if behavior == "large":
        payload = b"x" * (64 * 1024 * 1024)
        ready.touch()
        deadline = time.monotonic() + 5.0
        while not release.exists():
            if time.monotonic() >= deadline:
                raise RuntimeError("large-result release was not signaled")
            time.sleep(0.005)
        return payload
    deadline = time.monotonic() + 5.0
    while not ready.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("large-result worker did not become ready")
        time.sleep(0.005)
    threading.Thread(
        target=_touch_after_delay,
        args=(release_text,),
        daemon=True,
    ).start()
    return 1


def _stubborn_worker(case: tuple[str, str], _logfn) -> int:
    behavior, marker_text = case
    marker = Path(marker_text)
    if behavior == "block":
        if os.name != "nt":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        marker.touch()
        while True:
            time.sleep(0.05)
    deadline = time.monotonic() + 5.0
    while not marker.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("blocking worker did not become ready")
        time.sleep(0.01)
    return 1


def _worker_resource_state() -> tuple[set[int], set[int]]:
    process_ids = {
        int(process.pid)
        for process in mp.active_children()
        if process.pid is not None
    }
    feeder_ids = {
        int(thread.ident)
        for thread in threading.enumerate()
        if thread.name == "QueueFeederThread" and thread.ident is not None
    }
    return process_ids, feeder_ids


class SchedulerTests(unittest.TestCase):
    def assert_no_new_worker_resources(
        self,
        before: tuple[set[int], set[int]],
    ) -> None:
        deadline = time.monotonic() + 2.0
        while True:
            after = _worker_resource_state()
            new_processes = after[0] - before[0]
            new_feeders = after[1] - before[1]
            if not new_processes and not new_feeders:
                return
            if time.monotonic() >= deadline:
                self.fail(
                    f"worker resources leaked: processes={sorted(new_processes)}, "
                    f"queue_feeders={sorted(new_feeders)}"
                )
            time.sleep(0.02)

    def test_chunk_environment_precedence_and_validation(self) -> None:
        environment = {
            "PANELSOLVER_PARALLEL_CHUNK_CASES": "3",
            "FMFSOLVER_PARALLEL_CHUNK_CASES": "4",
            "NEWTSOLVER_PARALLEL_CHUNK_CASES": "5",
        }
        self.assertEqual(2, resolve_parallel_chunk_cases(2, environment=environment))
        self.assertEqual(
            3,
            resolve_parallel_chunk_cases(
                legacy_env_prefix="FMFSOLVER",
                environment=environment,
            ),
        )
        self.assertEqual(
            4,
            resolve_parallel_chunk_cases(
                legacy_env_prefix="FMFSOLVER",
                environment={"FMFSOLVER_PARALLEL_CHUNK_CASES": "4"},
            ),
        )
        self.assertEqual(
            8,
            resolve_parallel_chunk_cases(
                environment={"NEWTSOLVER_PARALLEL_CHUNK_CASES": "99"}
            ),
        )
        with self.assertRaisesRegex(SchedulerError, "PANELSOLVER"):
            resolve_parallel_chunk_cases(
                environment={"PANELSOLVER_PARALLEL_CHUNK_CASES": "0"}
            )
        with self.assertRaisesRegex(SchedulerError, "legacy_env_prefix"):
            resolve_parallel_chunk_cases(legacy_env_prefix="UNKNOWN")

    def test_completion_progress_logs_and_ordered_snapshots(self) -> None:
        before = _worker_resource_state()
        logs: list[str] = []
        progress = []
        snapshots = []
        cases = ((0, 0.15), (1, 0.0), (2, 0.02))
        results = list(
            iter_case_results_parallel(
                cases,
                2,
                _success_worker,
                log_policy=WorkerLogPolicy.FORWARD,
                partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                execution_order=(2, 0, 1),
                chunk_cases=1,
                logfn=logs.append,
                progress_cb=progress.append,
                snapshot_cb=snapshots.append,
            )
        )
        self.assertEqual({(0, 0), (1, 10), (2, 20)}, set(results))
        self.assertEqual([1, 2, 3], [event.completed for event in progress])
        self.assertEqual(3, progress[-1].total)
        self.assertEqual({"case=0", "case=1", "case=2"}, set(logs))
        self.assertEqual(((2, 20), (0, 0), (1, 10)), snapshots[-1])
        self.assertEqual(
            ((2, 20), (0, 0), (1, 10)),
            ordered_success_snapshot(dict(results), (2, 0, 1)),
        )
        self.assert_no_new_worker_resources(before)

    def test_forward_logs_and_discard_failed_chunk_results(self) -> None:
        before = _worker_resource_state()
        logs: list[str] = []
        yielded: list[tuple[int, int]] = []
        iterator = iter_case_results_parallel(
            (0, 1, 2),
            2,
            _failure_worker,
            log_policy=WorkerLogPolicy.FORWARD,
            partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
            bucket_keys=("same", "same", "same"),
            chunk_cases=3,
            logfn=logs.append,
        )
        with self.assertRaises(WorkerExecutionError) as caught:
            yielded.extend(iterator)
        self.assertEqual([], yielded)
        self.assertEqual(["case=0", "case=1"], logs)
        self.assertIn("deliberate worker failure", caught.exception.remote_error)
        self.assertIn("ValueError", caught.exception.remote_traceback)
        self.assert_no_new_worker_resources(before)

    def test_drop_logs_and_yield_completed_failed_chunk_results(self) -> None:
        before = _worker_resource_state()
        logs: list[str] = []
        iterator = iter_case_results_parallel(
            (0, 1, 2),
            2,
            _failure_worker,
            log_policy=WorkerLogPolicy.DROP,
            partial_result_policy=PartialResultPolicy.YIELD_COMPLETED,
            bucket_keys=("same", "same", "same"),
            chunk_cases=3,
            logfn=logs.append,
        )
        self.assertEqual((0, 0), next(iterator))
        with self.assertRaises(WorkerExecutionError):
            next(iterator)
        self.assertEqual([], logs)
        self.assert_no_new_worker_resources(before)

    def test_cancellation_waits_for_case_boundary_and_stops_dispatch(self) -> None:
        before = _worker_resource_state()
        progress = []
        yielded: list[tuple[int, int]] = []

        def cancel_after_first_completion() -> bool:
            return bool(progress)

        iterator = iter_case_results_parallel(
            ((0, 0.02), (1, 0.15), (2, 0.15), (3, 0.15)),
            2,
            _success_worker,
            log_policy=WorkerLogPolicy.DROP,
            partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
            chunk_cases=1,
            cancel_cb=cancel_after_first_completion,
            progress_cb=progress.append,
        )
        with self.assertRaises(SchedulerCancelled):
            yielded.extend(iterator)
        self.assertGreaterEqual(len(yielded), 1)
        self.assertLess(len(yielded), 4)
        self.assertEqual(list(range(1, len(yielded) + 1)), [p.completed for p in progress])
        self.assert_no_new_worker_resources(before)

    def test_unexpected_exit_is_reported_with_exit_code(self) -> None:
        before = _worker_resource_state()
        with self.assertRaises(WorkerUnexpectedExitError) as caught:
            list(
                iter_case_results_parallel(
                    (0, 1),
                    2,
                    _unexpected_exit_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    chunk_cases=1,
                )
            )
        self.assertIn((0, 7), caught.exception.exits)
        self.assert_no_new_worker_resources(before)

    def test_fast_unexpected_exit_is_repeatable_after_all_workers_are_ready(
        self,
    ) -> None:
        before = _worker_resource_state()
        for _ in range(5):
            with self.assertRaises(WorkerUnexpectedExitError):
                list(
                    iter_case_results_parallel(
                        (0, 1),
                        2,
                        _unexpected_exit_worker,
                        log_policy=WorkerLogPolicy.DROP,
                        partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                        chunk_cases=1,
                    )
                )
        self.assert_no_new_worker_resources(before)

    def test_unpickleable_result_is_a_bounded_worker_error(self) -> None:
        before = _worker_resource_state()
        with self.assertRaisesRegex(WorkerExecutionError, "serialize worker chunk_done"):
            list(
                iter_case_results_parallel(
                    ("result", "ok"),
                    2,
                    _unpickleable_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    bucket_keys=("same", "same"),
                    chunk_cases=2,
                )
            )
        self.assert_no_new_worker_resources(before)

    def test_unpickleable_case_is_rejected_before_pipe_dispatch(self) -> None:
        before = _worker_resource_state()
        unpickleable_case = lambda: None
        with self.assertRaisesRegex(SchedulerError, "serialize worker task"):
            list(
                iter_case_results_parallel(
                    (unpickleable_case, 1),
                    2,
                    _identity_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    chunk_cases=1,
                )
            )
        self.assert_no_new_worker_resources(before)

    def test_unpickleable_partial_result_is_a_bounded_delivery_error(
        self,
    ) -> None:
        before = _worker_resource_state()
        yielded = []
        iterator = iter_case_results_parallel(
            ("result", "error"),
            2,
            _unpickleable_worker,
            log_policy=WorkerLogPolicy.DROP,
            partial_result_policy=PartialResultPolicy.YIELD_COMPLETED,
            bucket_keys=("same", "same"),
            chunk_cases=2,
        )
        with self.assertRaisesRegex(
            WorkerExecutionError,
            "serialize worker error",
        ) as caught:
            yielded.extend(iterator)
        self.assertEqual([], yielded)
        self.assertIn(
            "failure after an unpickleable partial result",
            str(caught.exception),
        )
        self.assert_no_new_worker_resources(before)

    def test_early_close_interrupts_a_backpressured_large_result(self) -> None:
        before = _worker_resource_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ready = str(root / "large-ready")
            release = str(root / "large-release")
            iterator = iter_case_results_parallel(
                (("large", ready, release), ("fast", ready, release)),
                2,
                _large_result_worker,
                log_policy=WorkerLogPolicy.DROP,
                partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                bucket_keys=("large", "fast"),
                chunk_cases=1,
            )
            self.assertEqual((1, 1), next(iterator))
            time.sleep(0.05)
            started = time.monotonic()
            iterator.close()
            self.assertLess(time.monotonic() - started, 7.0)
        self.assert_no_new_worker_resources(before)

    def test_unpickleable_forwarded_log_is_a_bounded_worker_error(self) -> None:
        before = _worker_resource_state()
        with self.assertRaisesRegex(WorkerExecutionError, "serialize worker chunk_done"):
            list(
                iter_case_results_parallel(
                    ("log", "ok"),
                    2,
                    _unpickleable_worker,
                    log_policy=WorkerLogPolicy.FORWARD,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    bucket_keys=("same", "same"),
                    chunk_cases=2,
                )
            )
        self.assert_no_new_worker_resources(before)

    def test_early_iterator_close_kills_and_reaps_a_resistant_worker(self) -> None:
        before = _worker_resource_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            marker = str(Path(temp_dir) / "blocking-worker-ready")
            iterator = iter_case_results_parallel(
                (("block", marker), ("fast", marker)),
                2,
                _stubborn_worker,
                log_policy=WorkerLogPolicy.DROP,
                partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                bucket_keys=("block", "fast"),
                chunk_cases=1,
            )
            self.assertEqual((1, 1), next(iterator))
            started = time.monotonic()
            iterator.close()
            self.assertLess(time.monotonic() - started, 7.0)
        self.assert_no_new_worker_resources(before)

    def test_cleanup_failure_during_generator_close_is_not_hidden(self) -> None:
        before = _worker_resource_state()
        original_cleanup = scheduler_module._cleanup_workers

        def cleanup_with_report(*args):
            errors = original_cleanup(*args)
            return (*errors, "synthetic cleanup failure")

        with mock.patch.object(
            scheduler_module,
            "_cleanup_workers",
            side_effect=cleanup_with_report,
        ):
            iterator = iter_case_results_parallel(
                ((0, 0.0), (1, 0.1)),
                2,
                _success_worker,
                log_policy=WorkerLogPolicy.DROP,
                partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                chunk_cases=1,
            )
            next(iterator)
            with self.assertRaisesRegex(SchedulerError, "synthetic cleanup failure"):
                iterator.close()
        self.assert_no_new_worker_resources(before)

    def test_cleanup_reports_a_process_that_survives_kill_without_blocking(self) -> None:
        calls: list[str] = []

        class FakeEvent:
            def set(self) -> None:
                calls.append("cancel")

        class FakeConnection:
            def __init__(self, name: str) -> None:
                self.name = name

            def send_bytes(self, _payload: bytes) -> None:
                calls.append(f"{self.name}:send")

            def close(self) -> None:
                calls.append(f"{self.name}:close")

        class FakeProcess:
            pid = 4242

            def is_alive(self) -> bool:
                return True

            def join(self, timeout=None) -> None:
                calls.append(f"join:{timeout is not None}")

            def terminate(self) -> None:
                calls.append("terminate")

            def kill(self) -> None:
                calls.append("kill")

            def close(self) -> None:
                calls.append("process:close")

        errors = scheduler_module._cleanup_workers(
            FakeEvent(),
            (FakeConnection("task"),),
            (FakeConnection("result"),),
            (FakeConnection("child"),),
            (FakeProcess(),),
        )
        self.assertTrue(any("remained alive after kill" in error for error in errors))
        self.assertIn("terminate", calls)
        self.assertIn("kill", calls)
        self.assertNotIn("task:send", calls)
        self.assertNotIn("process:close", calls)
        self.assertTrue(all(call == "join:True" for call in calls if call.startswith("join")))

    def test_mid_frame_connection_failure_is_a_worker_exit_error(self) -> None:
        before = _worker_resource_state()
        connection_base = scheduler_module.mp.connection._ConnectionBase
        original_recv_bytes = connection_base.recv_bytes
        failed = False

        def fail_after_readiness(connection, *args, **kwargs):
            nonlocal failed
            payload = original_recv_bytes(connection, *args, **kwargs)
            message = scheduler_module._decode_worker_message(payload)
            if message.get("type") != "ready" and not failed:
                failed = True
                raise OSError("got end of file during message")
            return payload

        with mock.patch.object(
            connection_base,
            "recv_bytes",
            new=fail_after_readiness,
        ):
            with self.assertRaises(WorkerUnexpectedExitError):
                list(
                    iter_case_results_parallel(
                        ((0, 0.0), (1, 0.05)),
                        2,
                        _success_worker,
                        log_policy=WorkerLogPolicy.DROP,
                        partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                        chunk_cases=1,
                    )
                )
        self.assertTrue(failed)
        self.assert_no_new_worker_resources(before)

    def test_unpickleable_spawn_callable_is_rejected_before_child_start(self) -> None:
        before = _worker_resource_state()
        local_worker = lambda case, _logfn: case
        with self.assertRaisesRegex(
            WorkerStartupError,
            "serialize spawn worker callable",
        ):
            list(
                iter_case_results_parallel(
                    (0, 1),
                    2,
                    local_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                )
            )
        self.assert_no_new_worker_resources(before)

    def test_os_spawn_start_failure_is_wrapped_without_child_leak(self) -> None:
        before = _worker_resource_state()
        process_type = scheduler_module.mp.get_context("spawn").Process
        original_start = process_type.start
        calls = 0

        def fail_first_start(process):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("synthetic spawn failure")
            return original_start(process)

        with mock.patch.object(process_type, "start", new=fail_first_start):
            with self.assertRaisesRegex(WorkerStartupError, "synthetic spawn failure"):
                list(
                    iter_case_results_parallel(
                        (0, 1),
                        2,
                        _identity_worker,
                        log_policy=WorkerLogPolicy.DROP,
                        partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    )
                )
        self.assertEqual(1, calls)
        self.assert_no_new_worker_resources(before)

    def test_requires_explicit_policies_and_valid_complete_order(self) -> None:
        with self.assertRaisesRegex(SchedulerError, "log_policy"):
            list(
                iter_case_results_parallel(
                    (0, 1),
                    2,
                    _failure_worker,
                    log_policy="merge",
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                )
            )
        with self.assertRaisesRegex(SchedulerError, "exactly once"):
            list(
                iter_case_results_parallel(
                    (0, 1),
                    2,
                    _failure_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                    execution_order=(0, 0),
                )
            )


if __name__ == "__main__":
    unittest.main()
