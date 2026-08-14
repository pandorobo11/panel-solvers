from __future__ import annotations

import gc
import multiprocessing as mp
import os
import queue
import sys
import tempfile
import threading
import time
import traceback
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import panelsolver.app.runtime as runtime_module
import panelsolver.core.scheduler as scheduler_module
from fmfsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_fmf_results,
)
from fmfsolver.core.solver import run_case as run_fmf_case
from fmfsolver.core.solver import run_cases as run_fmf_cases
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from newtsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_newt_results,
)
from newtsolver.core.solver import run_case as run_newt_case
from newtsolver.core.solver import run_cases as run_newt_cases
from newtsolver.io.io_cases import read_cases as read_newt_cases
from panelsolver.app.legacy_results import run_legacy_cases
from panelsolver.app.legacy_scheduler import translate_legacy_scheduler_error
from panelsolver.core import (
    CsvProjection,
    MeshLoadError,
    SchedulerError,
    WorkerExecutionError,
    WorkerStartupError,
    WorkerUnexpectedExitError,
)
from tests.current_case_fixtures import read_current_cases

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"
_ORIGINAL_WORKER_PROCESS_ENTRY = scheduler_module._worker_process_entry


def _delayed_ready_process_entry(*args) -> None:
    time.sleep(0.5)
    _ORIGINAL_WORKER_PROCESS_ENTRY(*args)


def _pre_ready_exit_process_entry(worker_id, *args) -> None:
    if worker_id == 0:
        os._exit(7)
    time.sleep(0.5)
    _ORIGINAL_WORKER_PROCESS_ENTRY(worker_id, *args)


def _public_worker_failure(row, logfn):
    case_id = str(row["case_id"])
    logfn(f"case={case_id}")
    if case_id == "bad":
        raise ValueError("public wrapper failure")
    return {"case_id": case_id}


def _unexpected_exit_worker(row, _logfn):
    if str(row["case_id"]) == "crash":
        os._exit(7)
    time.sleep(0.3)
    return {"case_id": str(row["case_id"])}


def _unpickleable_result_worker(row, _logfn):
    if str(row["case_id"]) == "unpickleable":
        return lambda: None
    time.sleep(0.1)
    return {"case_id": str(row["case_id"])}


def _blocking_prepared_case(prepared, _logfn):
    marker_dir = Path(str(prepared.row["phase8_cancel_marker_dir"]))
    (marker_dir / str(prepared.row["case_id"])).touch()
    time.sleep(30.0)
    raise AssertionError("compatibility cancellation did not stop the worker")


def _post_yield_success_prepared_case(prepared, _logfn):
    case_id = str(prepared.row["case_id"])
    _logfn(f"[worker] case_id={case_id}")
    projection = CsvProjection(
        ("case_id", "scope"),
        ({"case_id": case_id, "scope": "total"},),
    )
    return runtime_module.ProductCaseRunResult(projection, "")


def _resource_state() -> tuple[tuple[int, ...], tuple[int, ...]]:
    children = tuple(
        sorted(
            int(process.pid)
            for process in mp.active_children()
            if process.pid is not None
        )
    )
    feeders = tuple(
        sorted(
            int(thread.ident)
            for thread in threading.enumerate()
            if thread.name == "QueueFeederThread" and thread.ident is not None
        )
    )
    return children, feeders


def _scheduler_frame(case_ids: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "case_id": case_id,
            "shielding_on": 1,
            "stl_path": "same.stl",
            "stl_scale_m_per_unit": 1.0,
            "alpha_deg": 0.0,
            "beta_or_bank_deg": 0.0,
            "attitude_input": "beta_tan",
            "ray_backend": "rtree",
        }
        for case_id in case_ids
    )


def _missing_error(path: Path) -> FileNotFoundError:
    try:
        path.resolve().open("rb")
    except FileNotFoundError as exc:
        return exc
    raise AssertionError("missing-path fixture unexpectedly exists")


class Phase8DirectErrorCompatibilityTests(unittest.TestCase):
    def assert_exact_exception(
        self,
        exc: BaseException,
        expected_type: type[BaseException],
        expected_message: str,
    ) -> None:
        self.assertIs(type(exc), expected_type)
        self.assertEqual(expected_message, str(exc))
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)
        self.assertFalse(exc.__suppress_context__)

    def assert_resources_released(
        self,
        before: tuple[tuple[int, ...], tuple[int, ...]],
    ) -> None:
        deadline = time.monotonic() + 5.0
        while _resource_state() != before and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(before, _resource_state())

    @staticmethod
    def products():
        return (
            (
                "fmfsolver",
                read_fmf_cases,
                run_fmf_case,
                run_fmf_cases,
                "fmfsolver_cases.csv",
            ),
            (
                "newtsolver",
                read_newt_cases,
                run_newt_case,
                run_newt_cases,
                "newtsolver_cases.csv",
            ),
        )

    def test_empty_and_initial_cancel_restore_exact_runtime_error(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product, point="empty"):
                calls = 0

                def empty_cancel() -> bool:
                    nonlocal calls
                    calls += 1
                    return True

                with self.assertRaises(BaseException) as caught:
                    run_many(
                        pd.DataFrame(),
                        lambda _message: None,
                        cancel_cb=empty_cancel,
                    )
                self.assert_exact_exception(
                    caught.exception,
                    RuntimeError,
                    "Canceled by user.",
                )
                self.assertEqual(1, calls)

            with self.subTest(product=product, point="initial"):
                calls = 0
                logs: list[str] = []
                with tempfile.TemporaryDirectory() as temp_dir:
                    out_dir = Path(temp_dir) / "not-created"
                    row = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        out_dir=str(out_dir),
                        save_vtp_on=1,
                    )

                    def initial_cancel() -> bool:
                        nonlocal calls
                        calls += 1
                        return True

                    with self.assertRaises(BaseException) as caught:
                        run_many(
                            pd.DataFrame([row]),
                            logs.append,
                            cancel_cb=initial_cancel,
                        )
                    self.assert_exact_exception(
                        caught.exception,
                        RuntimeError,
                        "Canceled by user.",
                    )
                    self.assertEqual(1, calls)
                    self.assertEqual([], logs)
                    self.assertFalse(out_dir.exists())

    def test_empty_negative_flush_validation_precedes_cancellation(self) -> None:
        for product, _reader, _run_one, run_many, _filename in self.products():
            for requested in (False, True):
                with self.subTest(product=product, cancel_requested=requested):
                    calls = 0

                    def cancel(value=requested) -> bool:
                        nonlocal calls
                        calls += 1
                        return value

                    with self.assertRaises(BaseException) as caught:
                        run_many(
                            pd.DataFrame(),
                            lambda _message: None,
                            cancel_cb=cancel,
                            flush_every_cases=-1,
                        )
                    self.assert_exact_exception(
                        caught.exception,
                        ValueError,
                        "flush_every_cases must be >= 0.",
                    )
                    self.assertEqual(0, calls)

    def test_serial_boundary_cancel_retains_one_completed_checkpoint(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                before = _resource_state()
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    base = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                    rows = []
                    for index in range(2):
                        row = dict(base)
                        row.update(
                            case_id=f"{product}-boundary-{index}",
                            out_dir=str(root / f"out-{index}"),
                            shielding_on=0,
                            ray_backend="rtree",
                            save_vtp_on=1,
                        )
                        rows.append(row)
                    calls = 0
                    progress: list[tuple[int, int]] = []
                    snapshots: list[tuple[list[str], int, int, bool]] = []

                    def boundary_cancel() -> bool:
                        nonlocal calls
                        calls += 1
                        return calls >= 3

                    def snapshot(
                        frame,
                        done: int,
                        total: int,
                        final: bool,
                        sink=snapshots,
                    ) -> None:
                        sink.append(
                            (
                                frame.loc[
                                    frame["scope"] == "total", "case_id"
                                ].tolist(),
                                done,
                                total,
                                final,
                            )
                        )

                    with self.assertRaises(BaseException) as caught:
                        run_many(
                            pd.DataFrame(rows),
                            lambda _message: None,
                            workers=1,
                            progress_cb=lambda done, total, sink=progress: sink.append(
                                (done, total)
                            ),
                            cancel_cb=boundary_cancel,
                            flush_every_cases=1,
                            chunk_cb=snapshot,
                        )
                    self.assert_exact_exception(
                        caught.exception,
                        RuntimeError,
                        "Canceled by user.",
                    )
                    self.assertEqual(3, calls)
                    self.assertEqual([(1, 2)], progress)
                    self.assertEqual(
                        [([rows[0]["case_id"]], 1, 2, False)],
                        snapshots,
                    )
                    self.assertTrue(
                        (root / "out-0" / f"{rows[0]['case_id']}.vtp").is_file()
                    )
                    self.assertFalse((root / "out-1").exists())
                self.assert_resources_released(before)

    def test_inflight_parallel_cancel_does_not_accept_active_results(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                before = _resource_state()
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    marker_dir = root / "markers"
                    marker_dir.mkdir()
                    base = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                    rows = []
                    for index in range(2):
                        row = dict(base)
                        row.update(
                            case_id=f"{product}-inflight-{index}",
                            out_dir=str(root / f"out-{index}"),
                            shielding_on=0,
                            save_vtp_on=1,
                            phase8_cancel_marker_dir=str(marker_dir),
                        )
                        rows.append(row)
                    cancel_calls = 0
                    progress: list[tuple[int, int]] = []
                    snapshots: list[tuple[int, int, bool]] = []

                    def cancel_when_started(marker=marker_dir) -> bool:
                        nonlocal cancel_calls
                        cancel_calls += 1
                        return len(tuple(marker.iterdir())) == 2

                    started = time.monotonic()
                    with mock.patch.object(
                        runtime_module,
                        "_run_prepared_product_case",
                        new=_blocking_prepared_case,
                    ):
                        with self.assertRaises(BaseException) as caught:
                            run_many(
                                pd.DataFrame(rows),
                                lambda _message: None,
                                workers=2,
                                progress_cb=lambda done, total, sink=progress: sink.append(
                                    (done, total)
                                ),
                                cancel_cb=cancel_when_started,
                                flush_every_cases=1,
                                chunk_cb=lambda _frame, done, total, final, sink=snapshots: (
                                    sink.append((done, total, final))
                                ),
                            )
                    self.assertLess(time.monotonic() - started, 20.0)
                    self.assert_exact_exception(
                        caught.exception,
                        RuntimeError,
                        "Canceled by user.",
                    )
                    self.assertGreaterEqual(cancel_calls, 2)
                    self.assertEqual([], progress)
                    self.assertEqual([], snapshots)
                    self.assertFalse((root / "out-0").exists())
                    self.assertFalse((root / "out-1").exists())
                self.assert_resources_released(before)

    def test_direct_and_serial_missing_mesh_restore_file_not_found(self) -> None:
        for product, reader, run_one, run_many, filename in self.products():
            for api in ("run_case", "run_cases"):
                with self.subTest(product=product, api=api):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        root = Path(temp_dir)
                        missing = root / "missing.stl"
                        expected = _missing_error(missing)
                        out_dir = root / "out"
                        row = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                        row.update(
                            stl_path=str(missing),
                            out_dir=str(out_dir),
                            save_vtp_on=1,
                        )
                        with self.assertRaises(BaseException) as caught:
                            if api == "run_case":
                                run_one(row, lambda _message: None)
                            else:
                                run_many(
                                    pd.DataFrame([row]),
                                    lambda _message: None,
                                    workers=1,
                                )
                        self.assert_exact_exception(
                            caught.exception,
                            FileNotFoundError,
                            str(expected),
                        )
                        self.assertEqual(
                            str(missing.resolve()),
                            caught.exception.filename,
                        )
                        self.assertTrue(out_dir.is_dir())
                        self.assertEqual([], list(out_dir.iterdir()))

    def test_parallel_missing_mesh_restores_worker_error_first_line(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                before = _resource_state()
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    missing = root / "missing.stl"
                    expected = _missing_error(missing)
                    base = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                    rows = []
                    for index in range(2):
                        row = dict(base)
                        row.update(
                            case_id=f"{product}-missing-{index}",
                            stl_path=str(missing),
                            out_dir=str(root / f"out-{index}"),
                            shielding_on=1,
                            ray_backend="rtree",
                            save_vtp_on=1,
                        )
                        rows.append(row)
                    progress: list[tuple[int, int]] = []
                    snapshots: list[tuple[int, int, bool]] = []
                    with mock.patch.dict(
                        os.environ,
                        {"PANELSOLVER_PARALLEL_CHUNK_CASES": "2"},
                    ):
                        with self.assertRaises(BaseException) as caught:
                            run_many(
                                pd.DataFrame(rows),
                                lambda _message: None,
                                workers=2,
                                progress_cb=lambda done, total, sink=progress: (
                                    sink.append((done, total))
                                ),
                                flush_every_cases=1,
                                chunk_cb=lambda _frame, done, total, final, sink=snapshots: (
                                    sink.append((done, total, final))
                                ),
                            )
                    message = str(caught.exception)
                    self.assertIs(type(caught.exception), RuntimeError)
                    self.assertEqual(
                        f"[WorkerError] {expected}",
                        message.splitlines()[0],
                    )
                    self.assertIn("FileNotFoundError:", message)
                    self.assertIn("MeshLoadError:", message)
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertIsNone(caught.exception.__context__)
                    self.assertEqual([], progress)
                    self.assertEqual([], snapshots)
                    first_out = root / "out-0"
                    self.assertTrue(first_out.is_dir())
                    self.assertEqual([], list(first_out.iterdir()))
                    self.assertFalse((root / "out-1").exists())
                self.assert_resources_released(before)

    def test_public_worker_errors_retain_product_partial_and_log_policies(self) -> None:
        frame = _scheduler_frame(("good", "bad"))
        before = _resource_state()
        fmf_logs: list[str] = []
        fmf_results: list[tuple[int, dict]] = []
        fmf_iterator = iter_fmf_results(
            frame,
            [0, 1],
            2,
            _public_worker_failure,
            chunk_cases=2,
            logfn=fmf_logs.append,
        )
        with self.assertRaises(BaseException) as fmf_caught:
            fmf_results.extend(fmf_iterator)
        self.assertIs(type(fmf_caught.exception), RuntimeError)
        self.assertEqual(
            "[WorkerError] public wrapper failure",
            str(fmf_caught.exception).splitlines()[0],
        )
        self.assertIn("ValueError: public wrapper failure", str(fmf_caught.exception))
        self.assertIsNone(fmf_caught.exception.__cause__)
        self.assertIsNone(fmf_caught.exception.__context__)
        self.assertEqual([], fmf_results)
        self.assertEqual(["case=good", "case=bad"], fmf_logs)

        newt_iterator = iter_newt_results(
            frame,
            [0, 1],
            2,
            _public_worker_failure,
            chunk_cases=2,
        )
        self.assertEqual((0, {"case_id": "good"}), next(newt_iterator))
        with self.assertRaises(BaseException) as newt_caught:
            next(newt_iterator)
        self.assertIs(type(newt_caught.exception), RuntimeError)
        self.assertEqual(
            "[WorkerError] public wrapper failure",
            str(newt_caught.exception).splitlines()[0],
        )
        self.assertIn("ValueError: public wrapper failure", str(newt_caught.exception))
        self.assertIsNone(newt_caught.exception.__cause__)
        self.assertIsNone(newt_caught.exception.__context__)
        self.assert_resources_released(before)

    def test_public_fmf_log_callback_error_passes_through_by_identity(self) -> None:
        frame = _scheduler_frame(("good", "bad"))
        owned = SchedulerError("caller-owned FMF log failure")
        original_cause = ValueError("log cause")
        original_context = LookupError("log context")
        owned.__cause__ = original_cause
        owned.__context__ = original_context
        owned.__suppress_context__ = True

        def fail_log(_message: str) -> None:
            raise owned

        original_cleanup = scheduler_module._cleanup_workers

        def cleanup_with_note(*args):
            return (*original_cleanup(*args), "synthetic callback cleanup failure")

        before = _resource_state()
        with mock.patch.object(
            scheduler_module,
            "_cleanup_workers",
            side_effect=cleanup_with_note,
        ):
            with self.assertRaises(BaseException) as caught:
                list(
                    iter_fmf_results(
                        frame,
                        [0, 1],
                        2,
                        _public_worker_failure,
                        chunk_cases=2,
                        logfn=fail_log,
                    )
                )
        self.assertIs(owned, caught.exception)
        self.assertIs(original_cause, caught.exception.__cause__)
        self.assertIs(original_context, caught.exception.__context__)
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertEqual(
            ["Worker cleanup failed: synthetic callback cleanup failure"],
            caught.exception.__notes__,
        )
        self.assert_resources_released(before)

    def test_callback_sentinel_note_is_copied_to_original_exception(self) -> None:
        frame = pd.DataFrame([{"case_id": "callback-note"}])
        owned = SchedulerError("callback with cleanup note")

        def fail_log(_message: str) -> None:
            raise owned

        def fake_runtime(_rows, **runtime_kwargs):
            try:
                runtime_kwargs["logfn"]("trigger")
            except BaseException as wrapper:
                wrapper.add_note("Worker cleanup failed: simple sentinel note")
                raise
            raise AssertionError("callback unexpectedly returned")

        with self.assertRaises(BaseException) as caught:
            run_legacy_cases(
                frame,
                fake_runtime,
                legacy_env_prefix="FMFSOLVER",
                input_columns=("case_id",),
                logfn=fail_log,
            )
        self.assertIs(owned, caught.exception)
        self.assertEqual(
            ["Worker cleanup failed: simple sentinel note"],
            caught.exception.__notes__,
        )

    def test_parallel_post_yield_callbacks_retain_primary_and_cleanup_note(
        self,
    ) -> None:
        original_cleanup = scheduler_module._cleanup_workers

        def cleanup_with_note(*args):
            return (*original_cleanup(*args), "synthetic post-yield cleanup failure")

        for product, reader, _run_one, run_many, filename in self.products():
            for callback_point in ("progress_cb", "chunk_cb", "ok_logfn"):
                with self.subTest(product=product, callback=callback_point):
                    before = _resource_state()
                    with tempfile.TemporaryDirectory() as temp_dir:
                        root = Path(temp_dir)
                        base = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                        rows = []
                        for index in range(2):
                            row = dict(base)
                            row.update(
                                case_id=f"{product}-{callback_point}-{index}",
                                out_dir=str(root / f"out-{index}"),
                                shielding_on=0,
                                save_vtp_on=0,
                            )
                            rows.append(row)

                        owned = SchedulerError(
                            f"caller-owned {product} {callback_point} failure"
                        )
                        original_cause = ValueError("post-yield callback cause")
                        original_context = LookupError("post-yield callback context")
                        owned.__cause__ = original_cause
                        owned.__context__ = original_context
                        owned.__suppress_context__ = True
                        callback_calls = 0
                        observed_logs: list[str] = []

                        def fail_post_yield(
                            *args,
                            target=callback_point,
                            error=owned,
                            logs=observed_logs,
                        ):
                            nonlocal callback_calls
                            if target == "ok_logfn":
                                message = str(args[0])
                                logs.append(message)
                                if not message.startswith("[OK]"):
                                    return
                            callback_calls += 1
                            raise error

                        kwargs = {
                            "workers": 2,
                            "logfn": (
                                fail_post_yield
                                if callback_point == "ok_logfn"
                                else (lambda _message: None)
                            ),
                            "progress_cb": (
                                fail_post_yield
                                if callback_point == "progress_cb"
                                else None
                            ),
                            "flush_every_cases": (
                                1 if callback_point == "chunk_cb" else 0
                            ),
                            "chunk_cb": (
                                fail_post_yield
                                if callback_point == "chunk_cb"
                                else None
                            ),
                        }
                        unraisable: list[object] = []
                        with (
                            mock.patch.object(
                                runtime_module,
                                "_run_prepared_product_case",
                                new=_post_yield_success_prepared_case,
                            ),
                            mock.patch.object(
                                scheduler_module,
                                "_cleanup_workers",
                                side_effect=cleanup_with_note,
                            ),
                            mock.patch.object(
                                sys,
                                "unraisablehook",
                                new=unraisable.append,
                            ),
                        ):
                            caught_exception: BaseException | None = None
                            callback_traceback: tuple[str, ...] = ()
                            try:
                                run_many(pd.DataFrame(rows), **kwargs)
                            except BaseException as exc:
                                caught_exception = exc
                                callback_traceback = tuple(
                                    frame.name
                                    for frame in traceback.extract_tb(
                                        exc.__traceback__
                                    )
                                )
                            else:
                                self.fail("post-yield callback unexpectedly returned")
                            gc.collect()

                        self.assertIs(owned, caught_exception)
                        self.assertEqual(1, callback_calls)
                        self.assertIs(original_cause, owned.__cause__)
                        self.assertIs(original_context, owned.__context__)
                        self.assertTrue(owned.__suppress_context__)
                        self.assertIn("fail_post_yield", callback_traceback)
                        self.assertEqual(
                            [
                                (
                                    "Worker cleanup failed: synthetic post-yield "
                                    "cleanup failure"
                                )
                            ],
                            owned.__notes__,
                        )
                        if callback_point == "ok_logfn":
                            self.assertTrue(
                                any(message.startswith("[OK]") for message in observed_logs)
                            )
                            self.assertTrue(
                                any(
                                    message.startswith("[worker]")
                                    for message in observed_logs
                                )
                            )
                        self.assertEqual([], unraisable)
                        self.assertEqual([], list(root.rglob("*.vtp")))
                        self.assertEqual([], list(root.rglob("*.npz")))
                    self.assert_resources_released(before)

    def test_serial_post_result_callback_needs_no_worker_cleanup(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                row = read_current_cases(reader, INPUTS / filename).iloc[0].to_dict()
                owned = SchedulerError(f"serial callback failure for {product}")

                def fail_progress(
                    _done: int,
                    _total: int,
                    error=owned,
                ) -> None:
                    raise error

                with (
                    mock.patch.object(
                        runtime_module,
                        "_run_prepared_product_case",
                        new=_post_yield_success_prepared_case,
                    ),
                    mock.patch.object(
                        scheduler_module,
                        "_cleanup_workers",
                    ) as cleanup,
                ):
                    with self.assertRaises(BaseException) as caught:
                        run_many(
                            pd.DataFrame([row]),
                            lambda _message: None,
                            workers=1,
                            progress_cb=fail_progress,
                        )
                self.assertIs(owned, caught.exception)
                cleanup.assert_not_called()

    def test_compat_readiness_cancel_is_immediate_bounded_and_reaped(self) -> None:
        frame = _scheduler_frame(("first", "second"))
        products = (
            ("fmfsolver", iter_fmf_results, {"logfn": lambda _message: None}),
            ("newtsolver", iter_newt_results, {}),
        )
        for product, iterator_fn, extra in products:
            with self.subTest(product=product):
                before = _resource_state()
                calls = 0

                def cancel_during_readiness() -> bool:
                    nonlocal calls
                    calls += 1
                    return calls >= 2

                started = time.monotonic()
                with mock.patch.object(
                    scheduler_module,
                    "_worker_process_entry",
                    new=_delayed_ready_process_entry,
                ):
                    with self.assertRaises(BaseException) as caught:
                        list(
                            iterator_fn(
                                frame,
                                [0, 1],
                                2,
                                _public_worker_failure,
                                chunk_cases=1,
                                cancel_cb=cancel_during_readiness,
                                **extra,
                            )
                        )
                self.assertLess(time.monotonic() - started, 20.0)
                self.assert_exact_exception(
                    caught.exception,
                    RuntimeError,
                    "Canceled by user.",
                )
                self.assertGreaterEqual(calls, 2)
                self.assert_resources_released(before)

    def test_compat_pre_ready_exit_uses_product_unexpected_grammar(self) -> None:
        frame = _scheduler_frame(("first", "second"))
        products = (
            (
                "fmfsolver",
                iter_fmf_results,
                {"logfn": lambda _message: None},
                "[WorkerError] Worker exited unexpectedly: worker 0 exitcode=7",
            ),
            (
                "newtsolver",
                iter_newt_results,
                {},
                "[WorkerError] worker 0 (exit code 7) exited without returning a result.",
            ),
        )
        for product, iterator_fn, extra, expected in products:
            with self.subTest(product=product):
                before = _resource_state()
                with mock.patch.object(
                    scheduler_module,
                    "_worker_process_entry",
                    new=_pre_ready_exit_process_entry,
                ):
                    with self.assertRaises(BaseException) as caught:
                        list(
                            iterator_fn(
                                frame,
                                [0, 1],
                                2,
                                _public_worker_failure,
                                chunk_cases=1,
                                **extra,
                            )
                        )
                self.assertIs(type(caught.exception), RuntimeError)
                self.assertEqual(expected, str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)
                self.assertIs(type(caught.exception.__context__), queue.Empty)
                self.assertFalse(caught.exception.__suppress_context__)
                self.assert_resources_released(before)

    def test_public_startup_failures_restore_raw_legacy_exceptions(self) -> None:
        frame = _scheduler_frame(("first", "second"))
        wrappers = (
            ("fmfsolver", iter_fmf_results, {"logfn": lambda _message: None}),
            ("newtsolver", iter_newt_results, {}),
        )
        for product, iterator_fn, extra in wrappers:
            with self.subTest(product=product, failure="Process.start"):
                before = _resource_state()
                process_type = scheduler_module.mp.get_context("spawn").Process
                with mock.patch.object(
                    process_type,
                    "start",
                    side_effect=OSError("synthetic spawn failure"),
                ):
                    with self.assertRaises(BaseException) as caught:
                        list(
                            iterator_fn(
                                frame,
                                [0, 1],
                                2,
                                _public_worker_failure,
                                chunk_cases=1,
                                **extra,
                            )
                        )
                self.assert_exact_exception(
                    caught.exception,
                    OSError,
                    "synthetic spawn failure",
                )
                self.assert_resources_released(before)

            with self.subTest(product=product, failure="unpickleable callable"):
                before = _resource_state()
                local_worker = lambda row, _logfn: row
                try:
                    mp.reduction.ForkingPickler.dumps(local_worker)
                except BaseException as expected:
                    expected_type = type(expected)
                    expected_message = str(expected)
                else:
                    self.fail("local worker unexpectedly serialized")
                with self.assertRaises(BaseException) as caught:
                    list(
                        iterator_fn(
                            frame,
                            [0, 1],
                            2,
                            local_worker,
                            chunk_cases=1,
                            **extra,
                        )
                    )
                self.assert_exact_exception(
                    caught.exception,
                    expected_type,
                    expected_message,
                )
                self.assert_resources_released(before)

    def test_public_unexpected_exit_retains_product_message_grammar(self) -> None:
        frame = _scheduler_frame(("crash", "wait"))
        products = (
            (
                "fmfsolver",
                iter_fmf_results,
                {"logfn": lambda _message: None},
                "[WorkerError] Worker exited unexpectedly: worker 0 exitcode=7",
            ),
            (
                "newtsolver",
                iter_newt_results,
                {},
                "[WorkerError] worker 0 (exit code 7) exited without returning a result.",
            ),
        )
        for product, iterator_fn, extra, expected in products:
            with self.subTest(product=product):
                before = _resource_state()
                with self.assertRaises(BaseException) as caught:
                    list(
                        iterator_fn(
                            frame,
                            [0, 1],
                            2,
                            _unexpected_exit_worker,
                            chunk_cases=1,
                            **extra,
                        )
                    )
                self.assertIs(type(caught.exception), RuntimeError)
                self.assertEqual(expected, str(caught.exception))
                self.assertIs(type(caught.exception.__cause__), EOFError)
                self.assertIs(
                    caught.exception.__cause__,
                    caught.exception.__context__,
                )
                self.assertTrue(caught.exception.__suppress_context__)
                self.assert_resources_released(before)

    def test_poll_detected_unexpected_exit_restores_empty_queue_context(self) -> None:
        products = (
            (
                "FMFSOLVER",
                "[WorkerError] Worker exited unexpectedly: worker 0 exitcode=7",
            ),
            (
                "NEWTSOLVER",
                "[WorkerError] worker 0 (exit code 7) exited without returning a result.",
            ),
        )
        for legacy_env_prefix, expected in products:
            with self.subTest(legacy_env_prefix=legacy_env_prefix):
                shared = WorkerUnexpectedExitError(((0, 7),))
                translated = translate_legacy_scheduler_error(
                    shared,
                    legacy_env_prefix=legacy_env_prefix,
                )
                self.assertIs(type(translated), RuntimeError)
                self.assertEqual(expected, str(translated))
                self.assertIsNone(translated.__cause__)
                self.assertIs(type(translated.__context__), queue.Empty)
                self.assertEqual((), translated.__context__.args)
                self.assertEqual("", str(translated.__context__))
                self.assertFalse(translated.__suppress_context__)

    def test_new_safety_failure_is_bounded_built_in_runtime_error(self) -> None:
        frame = _scheduler_frame(("unpickleable", "wait"))
        wrappers = (
            ("fmfsolver", iter_fmf_results, {"logfn": lambda _message: None}),
            ("newtsolver", iter_newt_results, {}),
        )
        for product, iterator_fn, extra in wrappers:
            with self.subTest(product=product):
                before = _resource_state()
                with self.assertRaises(BaseException) as caught:
                    list(
                        iterator_fn(
                            frame,
                            [0, 1],
                            2,
                            _unpickleable_result_worker,
                            chunk_cases=1,
                            **extra,
                        )
                    )
                self.assertIs(type(caught.exception), RuntimeError)
                self.assertIn(
                    "Could not serialize worker chunk_done message",
                    str(caught.exception),
                )
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)
                self.assert_resources_released(before)

    def test_cleanup_diagnostic_note_survives_compatibility_translation(self) -> None:
        shared = WorkerExecutionError(0, "primary worker failure", "remote traceback")
        shared.add_note("Worker cleanup failed: synthetic cleanup failure")
        translated = translate_legacy_scheduler_error(
            shared,
            legacy_env_prefix="FMFSOLVER",
        )
        self.assertIs(type(translated), RuntimeError)
        self.assertEqual(
            ["Worker cleanup failed: synthetic cleanup failure"],
            translated.__notes__,
        )

    def test_transport_chain_replaces_legacy_queue_context_for_mid_frame_exit(
        self,
    ) -> None:
        transport = EOFError("synthetic mid-frame EOF")
        shared = WorkerUnexpectedExitError(((0, 7),))
        shared.__cause__ = transport
        shared.__context__ = transport
        shared.__suppress_context__ = True
        translated = translate_legacy_scheduler_error(
            shared,
            legacy_env_prefix="FMFSOLVER",
        )
        self.assertIs(type(translated), RuntimeError)
        self.assertIs(transport, translated.__cause__)
        self.assertIs(transport, translated.__context__)
        self.assertTrue(translated.__suppress_context__)

    def test_live_pre_ready_transport_chain_survives_both_product_boundaries(
        self,
    ) -> None:
        frame = _scheduler_frame(("first", "second"))
        products = (
            ("fmfsolver", iter_fmf_results, {"logfn": lambda _message: None}),
            ("newtsolver", iter_newt_results, {}),
        )
        for product, iterator_fn, extra in products:
            with self.subTest(product=product):
                before = _resource_state()

                def fail_readiness(
                    *_args,
                    product_id=product,
                    **_kwargs,
                ) -> None:
                    transport = EOFError(
                        f"synthetic live pre-ready EOF for {product_id}"
                    )
                    try:
                        raise transport
                    except EOFError as cause:
                        raise WorkerStartupError(
                            "Spawn worker 0 closed before reporting ready."
                        ) from cause

                with mock.patch.object(
                    scheduler_module,
                    "_wait_for_worker_readiness",
                    new=fail_readiness,
                ):
                    with self.assertRaises(BaseException) as caught:
                        list(
                            iterator_fn(
                                frame,
                                [0, 1],
                                2,
                                _public_worker_failure,
                                chunk_cases=1,
                                **extra,
                            )
                        )
                translated = caught.exception
                self.assertIs(type(translated), RuntimeError)
                self.assertEqual(
                    "Spawn worker 0 closed before reporting ready.",
                    str(translated),
                )
                self.assertIs(type(translated.__cause__), EOFError)
                self.assertIs(translated.__cause__, translated.__context__)
                self.assertEqual(
                    f"synthetic live pre-ready EOF for {product}",
                    str(translated.__cause__),
                )
                self.assertTrue(translated.__suppress_context__)
                self.assert_resources_released(before)

    def test_callback_owned_shared_errors_pass_through_by_identity(self) -> None:
        frame = pd.DataFrame([{"case_id": "callback-owned"}])
        projection = CsvProjection(
            ("case_id", "scope"),
            ({"case_id": "callback-owned", "scope": "total"},),
        )
        callback_points = ("logfn", "progress_cb", "cancel_cb", "chunk_cb")
        exception_types = (MeshLoadError, SchedulerError)

        for callback_point in callback_points:
            for exception_type in exception_types:
                with self.subTest(
                    callback=callback_point,
                    exception=exception_type.__name__,
                ):
                    owned = exception_type(
                        f"callback-owned {callback_point} {exception_type.__name__}"
                    )
                    original_cause = ValueError("callback cause")
                    original_context = LookupError("callback context")
                    owned.__cause__ = original_cause
                    owned.__context__ = original_context
                    owned.__suppress_context__ = True

                    def callback(*_args, error=owned):
                        raise error

                    def fake_runtime(
                        _rows,
                        callback_name=callback_point,
                        **runtime_kwargs,
                    ):
                        if callback_name == "logfn":
                            runtime_kwargs["logfn"]("worker log")
                        elif callback_name == "progress_cb":
                            runtime_kwargs["progress_cb"](1, 1)
                        elif callback_name == "cancel_cb":
                            runtime_kwargs["cancel_cb"]()
                        else:
                            runtime_kwargs["snapshot_cb"](
                                projection,
                                1,
                                1,
                                False,
                            )
                        raise AssertionError("callback unexpectedly returned")

                    with self.assertRaises(BaseException) as caught:
                        run_legacy_cases(
                            frame,
                            fake_runtime,
                            legacy_env_prefix="FMFSOLVER",
                            input_columns=("case_id",),
                            **{callback_point: callback},
                        )
                    self.assertIs(owned, caught.exception)
                    self.assertEqual(
                        f"callback-owned {callback_point} {exception_type.__name__}",
                        str(caught.exception),
                    )
                    self.assertIs(original_cause, caught.exception.__cause__)
                    self.assertIs(original_context, caught.exception.__context__)
                    self.assertTrue(caught.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
