from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import panelsolver.app.runtime as runtime_module
from fmfsolver.core.solver import run_case as run_fmf_case
from fmfsolver.core.solver import run_cases as run_fmf_cases
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from newtsolver.core.solver import run_case as run_newt_case
from newtsolver.core.solver import run_cases as run_newt_cases
from newtsolver.io.io_cases import read_cases as read_newt_cases
from panelsolver.core import clear_mesh_cache

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"
MESH_WARNING = "[WARN] Mesh is not watertight (trimesh). Continuing anyway."


def _backend_hint(product: str, *, embree: bool) -> str:
    if embree:
        return "[INFO] Ray backend: Embree (ray_pyembree)."
    return (
        "[INFO] Ray backend: rtree (ray_triangle). Optional acceleration is "
        "available: uv sync --extra rayaccel (or pip install "
        f'"{product}[rayaccel]").'
    )


class Phase8DirectLoggingCompatibilityTests(unittest.TestCase):
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

    def test_direct_case_logs_only_case_messages_and_does_not_consume_hint(self) -> None:
        for product, reader, run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    tempfile.TemporaryDirectory() as temp_dir,
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                ):
                    clear_mesh_cache()
                    row = reader(INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        out_dir=str(Path(temp_dir) / "direct"),
                        save_vtp_on=1,
                        save_npz_on=1,
                    )
                    logs: list[str] = []
                    result = run_one(row, logs.append)
                    self.assertEqual(row["case_id"], result["case_id"])
                    self.assertEqual([MESH_WARNING], logs)
                    self.assertEqual(set(), hinted)
                    self.assertTrue(Path(result["vtp_path"]).is_file())
                    self.assertTrue(Path(result["npz_path"]).is_file())

                    with mock.patch.object(
                        runtime_module.trimesh_ray,
                        "has_embree",
                        True,
                    ):
                        empty_logs: list[str] = []
                        empty = run_many(pd.DataFrame(), empty_logs.append)
                        self.assertTrue(empty.empty)
                        self.assertEqual(
                            [_backend_hint(product, embree=True)],
                            empty_logs,
                        )
                        self.assertEqual({product}, hinted)

                        hot_logs: list[str] = []
                        self.assertTrue(run_many(pd.DataFrame(), hot_logs.append).empty)
                        self.assertEqual([], hot_logs)

    def test_direct_pre_mesh_failure_logs_nothing_and_leaves_hint_cold(self) -> None:
        for product, reader, run_one, _run_many, filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    tempfile.TemporaryDirectory() as temp_dir,
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                ):
                    clear_mesh_cache()
                    root = Path(temp_dir)
                    row = reader(INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        stl_path=str(root / "missing.stl"),
                        out_dir=str(root / "out"),
                        save_vtp_on=0,
                        save_npz_on=0,
                    )
                    logs: list[str] = []
                    with self.assertRaises(FileNotFoundError):
                        run_one(row, logs.append)
                    self.assertEqual([], logs)
                    self.assertEqual(set(), hinted)

    def test_direct_log_callback_is_checked_only_when_a_case_message_is_emitted(
        self,
    ) -> None:
        for product, reader, run_one, _run_many, filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    tempfile.TemporaryDirectory() as temp_dir,
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                ):
                    row = reader(INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        out_dir=str(Path(temp_dir) / "direct"),
                        save_vtp_on=0,
                        save_npz_on=0,
                    )
                    clear_mesh_cache()
                    run_one(row, lambda _message: None)
                    self.assertEqual(row["case_id"], run_one(row, None)["case_id"])

                    clear_mesh_cache()
                    with self.assertRaises(TypeError) as caught:
                        run_one(row, None)
                    self.assertEqual(
                        "'NoneType' object is not callable",
                        str(caught.exception),
                    )
                    self.assertEqual(set(), hinted)

                    owned = LookupError(f"{product} direct warning callback")

                    def fail(_message: str, error: BaseException = owned) -> None:
                        raise error

                    clear_mesh_cache()
                    try:
                        run_one(row, fail)
                    except BaseException as caught:
                        self.assertIs(owned, caught)
                        self.assertIn("fail", traceback_names(caught))
                    else:
                        self.fail("direct warning callback exception was swallowed")
                    self.assertEqual(set(), hinted)

    def test_serial_batch_retains_hint_run_and_case_log_sequence(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    tempfile.TemporaryDirectory() as temp_dir,
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                    mock.patch.object(runtime_module.trimesh_ray, "has_embree", False),
                ):
                    clear_mesh_cache()
                    row = reader(INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        out_dir=str(Path(temp_dir) / "serial"),
                        save_vtp_on=0,
                        save_npz_on=0,
                    )
                    frame = pd.DataFrame([row])
                    cold_logs: list[str] = []
                    run_many(frame, cold_logs.append, workers=1)
                    self.assertEqual(
                        [
                            _backend_hint(product, embree=False),
                            f"[RUN] (1/1) case_id={row['case_id']}",
                            MESH_WARNING,
                        ],
                        cold_logs,
                    )
                    self.assertEqual({product}, hinted)

                    hot_logs: list[str] = []
                    run_many(frame, hot_logs.append, workers=1)
                    self.assertEqual(
                        [f"[RUN] (1/1) case_id={row['case_id']}"],
                        hot_logs,
                    )

    def test_serial_required_logger_is_lazy_across_hint_and_run_messages(self) -> None:
        for product, reader, _run_one, run_many, filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    tempfile.TemporaryDirectory() as temp_dir,
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                ):
                    row = reader(INPUTS / filename).iloc[0].to_dict()
                    row.update(
                        out_dir=str(Path(temp_dir) / "serial"),
                        save_vtp_on=0,
                        save_npz_on=0,
                    )
                    frame = pd.DataFrame([row])
                    with self.assertRaises(TypeError) as cold:
                        run_many(frame, None, workers=1)
                    self.assertEqual(
                        "'NoneType' object is not callable",
                        str(cold.exception),
                    )
                    self.assertEqual(set(), hinted)

                    runtime_module._RAY_ACCEL_HINTED_PRODUCTS.add(product)
                    with self.assertRaises(TypeError) as hot:
                        run_many(frame, None, workers=1)
                    self.assertEqual(
                        "'NoneType' object is not callable",
                        str(hot.exception),
                    )
                    self.assertFalse(Path(row["out_dir"]).exists())

    def test_empty_hint_callback_failure_preserves_identity_and_cold_state(self) -> None:
        for product, _reader, _run_one, run_many, _filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                owned = LookupError(f"{product} hint callback")

                def fail(_message: str, error: BaseException = owned) -> None:
                    raise error

                with (
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                    mock.patch.object(runtime_module.trimesh_ray, "has_embree", True),
                ):
                    try:
                        run_many(pd.DataFrame(), fail)
                    except BaseException as caught:
                        self.assertIs(owned, caught)
                        self.assertIn("fail", traceback_names(caught))
                    else:
                        self.fail("hint callback exception was swallowed")
                    self.assertEqual(set(), hinted)

                    retry_logs: list[str] = []
                    self.assertTrue(run_many(pd.DataFrame(), retry_logs.append).empty)
                    self.assertEqual([_backend_hint(product, embree=True)], retry_logs)
                    self.assertEqual({product}, hinted)

    def test_empty_required_logger_failure_does_not_consume_hint(self) -> None:
        for product, _reader, _run_one, run_many, _filename in self.products():
            with self.subTest(product=product):
                hinted: set[str] = set()
                with (
                    mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ),
                    mock.patch.object(runtime_module.trimesh_ray, "has_embree", True),
                ):
                    with self.assertRaises(TypeError) as caught:
                        run_many(pd.DataFrame(), None)
                    self.assertEqual(
                        "'NoneType' object is not callable",
                        str(caught.exception),
                    )
                    self.assertEqual(set(), hinted)

    def test_empty_hint_state_is_independent_between_products(self) -> None:
        hinted: set[str] = set()
        products = self.products()
        with (
            mock.patch.object(
                runtime_module,
                "_RAY_ACCEL_HINTED_PRODUCTS",
                hinted,
            ),
            mock.patch.object(runtime_module.trimesh_ray, "has_embree", True),
        ):
            for product, _reader, _run_one, run_many, _filename in products:
                logs: list[str] = []
                self.assertTrue(run_many(pd.DataFrame(), logs.append).empty)
                self.assertEqual([_backend_hint(product, embree=True)], logs)
            self.assertEqual({"fmfsolver", "newtsolver"}, hinted)
            for product, _reader, _run_one, run_many, _filename in products:
                with self.subTest(product=product, point="hot"):
                    logs: list[str] = []
                    self.assertTrue(run_many(pd.DataFrame(), logs.append).empty)
                    self.assertEqual([], logs)

    def test_validation_and_cancel_precede_empty_hint(self) -> None:
        for product, _reader, _run_one, run_many, _filename in self.products():
            for point in ("validation", "cancel"):
                with self.subTest(product=product, point=point):
                    hinted: set[str] = set()
                    logs: list[str] = []
                    with mock.patch.object(
                        runtime_module,
                        "_RAY_ACCEL_HINTED_PRODUCTS",
                        hinted,
                    ):
                        if point == "validation":
                            with self.assertRaisesRegex(
                                ValueError,
                                "flush_every_cases must be >= 0",
                            ):
                                run_many(
                                    pd.DataFrame(),
                                    logs.append,
                                    flush_every_cases=-1,
                                )
                        else:
                            with self.assertRaisesRegex(RuntimeError, "Canceled by user"):
                                run_many(
                                    pd.DataFrame(),
                                    logs.append,
                                    cancel_cb=lambda: True,
                                )
                        self.assertEqual([], logs)
                        self.assertEqual(set(), hinted)


def traceback_names(exc: BaseException) -> list[str]:
    names: list[str] = []
    current = exc.__traceback__
    while current is not None:
        names.append(current.tb_frame.f_code.co_name)
        current = current.tb_next
    return names


if __name__ == "__main__":
    unittest.main()
