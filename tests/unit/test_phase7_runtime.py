from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from fmfsolver.runtime import GUI_ADAPTERS as FMF_GUI_ADAPTERS
from fmfsolver.runtime import RUNTIME_POLICY as FMF_POLICY
from fmfsolver.runtime import run_cases as run_fmf_cases
from newtsolver.io.io_cases import read_cases as read_newt_cases
from newtsolver.runtime import RUNTIME_POLICY as NEWT_POLICY
from newtsolver.runtime import run_cases as run_newt_cases
from panelsolver.app import GuiRunRequest, run_and_write_product_cases
from panelsolver.core import (
    PartialResultPolicy,
    SchedulerCancelled,
    WorkerExecutionError,
    WorkerLogPolicy,
)

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"


class Phase7RuntimeTests(unittest.TestCase):
    def test_product_scheduler_policies_remain_independent(self) -> None:
        self.assertIs(WorkerLogPolicy.FORWARD, FMF_POLICY.worker_log_policy)
        self.assertIs(
            PartialResultPolicy.DISCARD_CHUNK,
            FMF_POLICY.partial_result_policy,
        )
        self.assertIs(WorkerLogPolicy.DROP, NEWT_POLICY.worker_log_policy)
        self.assertIs(
            PartialResultPolicy.YIELD_COMPLETED,
            NEWT_POLICY.partial_result_policy,
        )

    def test_artifacts_off_still_creates_directory_and_blank_csv_paths(self) -> None:
        row = read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[0].to_dict()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out_dir = root / "case_outputs"
            row.update(
                {
                    "out_dir": str(out_dir),
                    "save_vtp_on": 0,
                    "save_npz_on": 0,
                }
            )
            summary = root / "summary.csv"
            result = run_and_write_product_cases((row,), FMF_POLICY, summary)
            self.assertTrue(out_dir.is_dir())
            self.assertFalse((out_dir / "fmf_zero_plate.vtp").exists())
            self.assertFalse((out_dir / "fmf_zero_plate.npz").exists())
            self.assertEqual("", result.cases[0].vtp_path)
            self.assertEqual("", result.cases[0].npz_path)
            with summary.open(encoding="utf-8", newline="") as stream:
                total = next(csv.DictReader(stream))
            self.assertEqual("", total["vtp_path"])
            self.assertEqual("", total["npz_path"])

    def test_checkpoints_are_completed_snapshots_in_input_order(self) -> None:
        frame = read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[[0, 1, 4]]
        snapshots: list[tuple[list[str], int, bool]] = []

        def capture(projection, done: int, _total: int, final: bool) -> None:
            case_ids = [
                str(row["case_id"])
                for row in projection.rows
                if row["scope"] == "total"
            ]
            snapshots.append((case_ids, done, final))

        with tempfile.TemporaryDirectory() as temp_dir:
            frame["out_dir"] = temp_dir
            rows = tuple(frame.to_dict(orient="records"))
            run_fmf_cases(
                rows,
                workers=1,
                flush_every_cases=1,
                snapshot_cb=capture,
            )
        input_order = {str(row["case_id"]): index for index, row in enumerate(rows)}
        self.assertEqual([1, 2, 3, 3], [done for _, done, _ in snapshots])
        self.assertEqual([False, False, False, True], [final for _, _, final in snapshots])
        for case_ids, _, _ in snapshots:
            self.assertEqual(
                sorted(case_ids, key=input_order.__getitem__),
                case_ids,
            )
        self.assertEqual(
            [str(row["case_id"]) for row in rows],
            snapshots[-1][0],
        )

    def test_initial_cancellation_has_no_case_side_effect(self) -> None:
        row = read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[0].to_dict()
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "not-created"
            row["out_dir"] = str(out_dir)
            with self.assertRaises(SchedulerCancelled):
                run_fmf_cases((row,), cancel_cb=lambda: True)
            self.assertFalse(out_dir.exists())

    def test_failed_chunk_policy_controls_checkpoint_logs_and_partial_result(
        self,
    ) -> None:
        products = (
            (
                "fmfsolver",
                read_fmf_cases,
                "fmfsolver_cases.csv",
                FMF_POLICY,
                False,
            ),
            (
                "newtsolver",
                read_newt_cases,
                "newtsolver_cases.csv",
                NEWT_POLICY,
                True,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for product_id, reader, filename, policy, yields_completed in products:
                with self.subTest(product=product_id):
                    product_root = root / product_id
                    product_root.mkdir()
                    blocker = product_root / "not-a-directory"
                    blocker.write_text("worker failure fixture\n", encoding="utf-8")
                    case_output = product_root / "case-output"
                    summary = product_root / "summary.csv"
                    sentinel = b"pre-existing summary must remain unchanged\n"
                    summary.write_bytes(sentinel)

                    base = reader(INPUTS / filename).iloc[0].to_dict()
                    good = dict(base)
                    bad = dict(base)
                    good_id = f"{product_id}_good"
                    bad_id = f"{product_id}_bad"
                    good.update(
                        case_id=good_id,
                        shielding_on=1,
                        ray_backend="rtree",
                        out_dir=str(case_output),
                        save_vtp_on=1,
                        save_npz_on=1,
                    )
                    bad.update(
                        case_id=bad_id,
                        shielding_on=1,
                        ray_backend="rtree",
                        out_dir=str(blocker),
                        save_vtp_on=1,
                        save_npz_on=1,
                    )
                    logs: list[str] = []
                    progress: list[tuple[int, int]] = []

                    with mock.patch.dict(
                        os.environ,
                        {"PANELSOLVER_PARALLEL_CHUNK_CASES": "2"},
                    ):
                        with self.assertRaises(WorkerExecutionError) as caught:
                            run_and_write_product_cases(
                                (good, bad),
                                policy,
                                summary,
                                workers=2,
                                logfn=logs.append,
                                progress_cb=lambda done, total, sink=progress: sink.append(
                                    (done, total)
                                ),
                                flush_every_cases=1,
                                log_snapshots=True,
                            )

                    self.assertIn("FileExistsError", caught.exception.remote_traceback)
                    self.assertTrue((case_output / f"{good_id}.vtp").is_file())
                    self.assertTrue((case_output / f"{good_id}.npz").is_file())
                    self.assertTrue(blocker.is_file())
                    self.assertFalse(any("[SAVE] final" in message for message in logs))

                    if yields_completed:
                        self.assertEqual([(1, 2)], progress)
                        with summary.open(encoding="utf-8", newline="") as stream:
                            rows = tuple(csv.DictReader(stream))
                        self.assertEqual(
                            [good_id],
                            [row["case_id"] for row in rows if row["scope"] == "total"],
                        )
                        self.assertFalse(any(row["case_id"] == bad_id for row in rows))
                        self.assertTrue(
                            any("[SAVE] checkpoint 1/2" in message for message in logs)
                        )
                        self.assertTrue(
                            any("[OK] (1/2)" in message for message in logs)
                        )
                        self.assertFalse(
                            any(message.startswith("[WARN]") for message in logs)
                        )
                    else:
                        self.assertEqual([], progress)
                        self.assertEqual(sentinel, summary.read_bytes())
                        self.assertFalse(any("[SAVE]" in message for message in logs))
                        self.assertFalse(any("[OK]" in message for message in logs))
                        self.assertTrue(
                            any(message.startswith("[WARN]") for message in logs)
                        )

    def test_parallel_success_is_input_ordered_and_retains_worker_log_split(self) -> None:
        products = (
            (
                read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[[0, 1]],
                run_fmf_cases,
                True,
            ),
            (
                read_newt_cases(INPUTS / "newtsolver_cases.csv").iloc[[0, 1]],
                run_newt_cases,
                False,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for product_index, (frame, runner, forwards_worker_logs) in enumerate(
                products
            ):
                with self.subTest(runner=runner.__module__):
                    out_dir = Path(temp_dir) / str(product_index)
                    frame = frame.copy()
                    frame["out_dir"] = str(out_dir)
                    rows = tuple(frame.to_dict(orient="records"))
                    logs: list[str] = []
                    result = runner(rows, workers=2, logfn=logs.append)
                    self.assertEqual(
                        [str(row["case_id"]) for row in rows],
                        [str(case.csv.rows[0]["case_id"]) for case in result.cases],
                    )
                    self.assertEqual(
                        forwards_worker_logs,
                        any(message.startswith("[WARN]") for message in logs),
                    )

    def test_real_gui_adapters_read_run_write_and_return_first_artifact(self) -> None:
        rows = FMF_GUI_ADAPTERS.read_cases(INPUTS / "fmfsolver_cases.csv")
        self.assertEqual(6, len(rows))
        with tempfile.TemporaryDirectory() as temp_dir:
            row = dict(rows[0])
            row["out_dir"] = temp_dir
            output = Path(temp_dir) / "summary.csv"
            logs: list[str] = []
            progress: list[tuple[int, int]] = []
            result = FMF_GUI_ADAPTERS.run_cases(
                GuiRunRequest(
                    rows=(row,),
                    workers=1,
                    output_path=output,
                    log=logs.append,
                    progress=lambda done, total: progress.append((done, total)),
                    cancel_requested=lambda: False,
                )
            )
            self.assertTrue(output.exists())
            self.assertEqual(Path(temp_dir) / "fmf_zero_plate.vtp", result.first_vtp_path)
            self.assertEqual("fmf_zero_plate", result.first_case_row["case_id"])
            self.assertEqual([(1, 1)], progress)
            self.assertTrue(any("[SAVE] final" in message for message in logs))
            self.assertEqual(
                FMF_GUI_ADAPTERS.build_case_signatures(row).primary.digest,
                FMF_GUI_ADAPTERS.build_case_signatures(result.first_case_row).primary.digest,
            )


if __name__ == "__main__":
    unittest.main()
