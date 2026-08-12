from __future__ import annotations

import os
import time
import unittest

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


class SchedulerTests(unittest.TestCase):
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

    def test_drop_logs_and_discard_failed_chunk_results(self) -> None:
        logs: list[str] = []
        yielded: list[tuple[int, int]] = []
        iterator = iter_case_results_parallel(
            (0, 1, 2),
            2,
            _failure_worker,
            log_policy=WorkerLogPolicy.DROP,
            partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
            bucket_keys=("same", "same", "same"),
            chunk_cases=3,
            logfn=logs.append,
        )
        with self.assertRaises(WorkerExecutionError) as caught:
            yielded.extend(iterator)
        self.assertEqual([], yielded)
        self.assertEqual([], logs)
        self.assertIn("deliberate worker failure", caught.exception.remote_error)
        self.assertIn("ValueError", caught.exception.remote_traceback)

    def test_forward_logs_and_yield_completed_failed_chunk_results(self) -> None:
        logs: list[str] = []
        iterator = iter_case_results_parallel(
            (0, 1, 2),
            2,
            _failure_worker,
            log_policy=WorkerLogPolicy.FORWARD,
            partial_result_policy=PartialResultPolicy.YIELD_COMPLETED,
            bucket_keys=("same", "same", "same"),
            chunk_cases=3,
            logfn=logs.append,
        )
        self.assertEqual((0, 0), next(iterator))
        with self.assertRaises(WorkerExecutionError):
            next(iterator)
        self.assertEqual(["case=0", "case=1"], logs)

    def test_cancellation_waits_for_case_boundary_and_stops_dispatch(self) -> None:
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

    def test_unexpected_exit_is_reported_with_exit_code(self) -> None:
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

    def test_spawn_start_failure_is_wrapped(self) -> None:
        local_worker = lambda case, _logfn: case
        with self.assertRaises(WorkerStartupError):
            list(
                iter_case_results_parallel(
                    (0, 1),
                    2,
                    local_worker,
                    log_policy=WorkerLogPolicy.DROP,
                    partial_result_policy=PartialResultPolicy.DISCARD_CHUNK,
                )
            )

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
