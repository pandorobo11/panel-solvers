from __future__ import annotations

import ast
import csv
import importlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import pyvista as pv

import fmfsolver
import fmfsolver.io
import fmfsolver.io.exporters as fmf_exporters
import newtsolver
import newtsolver.io
import newtsolver.io.exporters as newt_exporters
import panelsolver.app
import panelsolver.core
from fmfsolver.core.case_signature import build_case_signature as build_fmf_signature
from fmfsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_fmf_case_results_parallel,
)
from fmfsolver.core.sentman_core import sentman_dC_dA_vector
from fmfsolver.core.solver import run_case as run_fmf_case
from fmfsolver.core.solver import run_cases as run_fmf_cases
from fmfsolver.io.csv_out import write_results_csv as write_fmf_results_csv
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from fmfsolver.physics.us1976 import load_us1976_tables, sample_at_altitude_km
from newtsolver.core.case_signature import build_case_signature as build_newt_signature
from newtsolver.core.panel_core import panel_force_density
from newtsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_newt_case_results_parallel,
)
from newtsolver.core.solver import run_case as run_newt_case
from newtsolver.core.solver import run_cases as run_newt_cases
from newtsolver.io.csv_out import write_results_csv as write_newt_results_csv
from newtsolver.io.io_cases import read_cases as read_newt_cases
from panelsolver.app.legacy_results import legacy_result_frame
from panelsolver.core import CsvProjection
from tests.current_case_fixtures import read_current_cases

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "phase1"
CONTRACTS = FIXTURES / "golden"
EXPORTER_MODULES = (fmf_exporters, newt_exporters)
DIRECT_COMPONENT_KEYS = [
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
]

PANEL_CORE_ALL = [
    "ATTITUDE_INPUT_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "LEEWARD_EQUATION_VALUES",
    "_resolve_attitude_mode",
    "normalize_windward_equation",
    "normalize_leeward_equation",
    "modified_newtonian_cp_max",
    "_oblique_theta_from_beta",
    "_tangent_wedge_detach_limit",
    "_weak_oblique_shock_beta",
    "tangent_wedge_pressure_coefficient",
    "_tangent_cone_detach_limit",
    "tangent_cone_pressure_coefficient",
    "_prandtl_meyer_nu",
    "_inverse_prandtl_meyer",
    "resolve_attitude_to_vhat",
    "panel_force_density",
    "stl_to_body",
    "rot_y",
]
PRESSURE_MODELS_ALL = [
    "modified_newtonian_cp_max",
    "_prandtl_meyer_nu",
    "_inverse_prandtl_meyer",
    "prandtl_meyer_pressure_coefficient",
    "_oblique_theta_from_beta",
    "_tangent_wedge_detach_limit",
    "_weak_oblique_shock_beta",
    "tangent_wedge_pressure_coefficient",
    "_tangent_cone_detach_limit",
    "tangent_cone_pressure_coefficient",
]


def _public_scheduler_good_then_fail(row, logfn):
    case_id = str(row["case_id"])
    logfn(f"case={case_id}")
    if case_id == "bad":
        raise ValueError("public wrapper failure")
    return {"case_id": case_id}


class Phase7PublicImportTests(unittest.TestCase):
    def test_exact_frozen_module_inventories_import(self) -> None:
        for product in ("fmfsolver", "newtsolver"):
            contract = json.loads(
                (CONTRACTS / product / "contracts.json").read_text(encoding="utf-8")
            )
            for module_name in contract["module_paths"]:
                with self.subTest(module=module_name):
                    self.assertIsNotNone(importlib.import_module(module_name))

    def test_root_versions_and_d025_exports_remain_product_specific(self) -> None:
        self.assertEqual(fmfsolver.__all__, [])
        self.assertEqual(newtsolver.__all__, [])
        self.assertEqual(fmfsolver.__version__, "1.3.8")
        self.assertEqual(newtsolver.__version__, "1.0.3")
        panel_core = importlib.import_module("newtsolver.core.panel_core")
        pressure_models = importlib.import_module("newtsolver.core.pressure_models")
        self.assertEqual(panel_core.__all__, PANEL_CORE_ALL)
        self.assertEqual(pressure_models.__all__, PRESSURE_MODELS_ALL)
        sentman = importlib.import_module("fmfsolver.core.sentman_core")
        self.assertFalse(hasattr(sentman, "panel_force_density"))

    def test_compatibility_frontends_do_not_duplicate_numerical_dependencies(self) -> None:
        prohibited = {"numpy", "pyvista", "scipy", "trimesh"}
        for package in (
            ROOT / "src" / "fmfsolver" / "core",
            ROOT / "src" / "newtsolver" / "core",
        ):
            for source in package.rglob("*.py"):
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
                imported = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.add(node.module.split(".")[0])
                with self.subTest(source=source.relative_to(ROOT)):
                    self.assertFalse(imported & prohibited)


class Phase7PublicBehaviorTests(unittest.TestCase):
    def test_direct_rows_reject_removed_npz_field_before_output_creation(self) -> None:
        products = (
            (read_fmf_cases, run_fmf_case, "fmfsolver_cases.csv"),
            (read_newt_cases, run_newt_case, "newtsolver_cases.csv"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for reader, runner, filename in products:
                base = read_current_cases(
                    reader, FIXTURES / "inputs" / filename
                ).iloc[0].to_dict()
                for value in (0, 1):
                    out_dir = root / Path(filename).stem / str(value)
                    row = dict(base, out_dir=str(out_dir), save_npz_on=value)
                    with self.subTest(filename=filename, value=value):
                        with self.assertRaisesRegex(
                            ValueError,
                            "save_npz_on has been removed",
                        ):
                            runner(row, lambda _message: None)
                        self.assertFalse(out_dir.exists())

    def test_public_parallel_wrappers_preserve_failed_chunk_policies(self) -> None:
        frame = pd.DataFrame(
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
            for case_id in ("good", "bad")
        )

        fmf_logs: list[str] = []
        fmf_results: list[tuple[int, dict]] = []
        fmf_iterator = iter_fmf_case_results_parallel(
            frame,
            [0, 1],
            2,
            _public_scheduler_good_then_fail,
            chunk_cases=2,
            logfn=fmf_logs.append,
        )
        with self.assertRaisesRegex(RuntimeError, "public wrapper failure"):
            fmf_results.extend(fmf_iterator)
        self.assertEqual([], fmf_results)
        self.assertEqual(["case=good", "case=bad"], fmf_logs)

        newt_iterator = iter_newt_case_results_parallel(
            frame,
            [0, 1],
            2,
            _public_scheduler_good_then_fail,
            chunk_cases=2,
        )
        self.assertEqual((0, {"case_id": "good"}), next(newt_iterator))
        with self.assertRaisesRegex(RuntimeError, "public wrapper failure"):
            next(newt_iterator)

    def test_model_specific_callable_signatures_retain_pinned_values(self) -> None:
        sentman = sentman_dC_dA_vector(
            np.array([1.0, 0.0, 0.0]),
            np.array([-1.0, 0.0, 0.0]),
            5.0,
            300.0,
            300.0,
            2.0,
        )
        np.testing.assert_allclose(
            sentman,
            np.array([1.1972453850905538, 0.0, 0.0]),
            rtol=0.0,
            atol=1.0e-15,
        )
        newtonian = panel_force_density(
            np.array([1.0, 0.0, 0.0]),
            np.array([[-1.0, 0.0, 0.0]]),
            2.0,
        )
        np.testing.assert_allclose(
            newtonian,
            np.array([[1.0, 0.0, 0.0]]),
            rtol=0.0,
            atol=0.0,
        )

    def test_direct_solvers_return_legacy_signatures_and_numerical_anchors(self) -> None:
        products = (
            (
                read_fmf_cases,
                run_fmf_case,
                build_fmf_signature,
                "fmfsolver_cases.csv",
                2.3944907701811076,
            ),
            (
                read_newt_cases,
                run_newt_case,
                build_newt_signature,
                "newtsolver_cases.csv",
                2.0,
            ),
        )
        for reader, runner, signature, filename, expected_ca in products:
            row = read_current_cases(
                reader, FIXTURES / "inputs" / filename
            ).iloc[0].to_dict()
            row.update(save_vtp_on=0)
            result = runner(row, lambda _message: None)
            with self.subTest(case_id=row["case_id"]):
                self.assertEqual(result["case_signature"], signature(row))
                self.assertEqual(result["scope"], "total")
                self.assertEqual(result["component_rows"], [])
                self.assertAlmostEqual(result["CA"], expected_ca, places=14)

    def test_direct_solvers_restore_exact_legacy_blanks_types_and_paths(self) -> None:
        products = (
            (
                "fmfsolver",
                read_fmf_cases,
                run_fmf_case,
                run_fmf_cases,
                "fmfsolver_cases.csv",
                0,
                3,
            ),
            (
                "newtsolver",
                read_newt_cases,
                run_newt_case,
                run_newt_cases,
                "newtsolver_cases.csv",
                0,
                6,
            ),
        )
        for product, reader, run_one, run_many, filename, single_index, multi_index in products:
            cases = read_current_cases(reader, FIXTURES / "inputs" / filename)
            for api, runner in (("run_case", run_one), ("run_cases", run_many)):
                for kind, index, save_artifacts in (
                    ("single", single_index, False),
                    ("multi", multi_index, True),
                ):
                    with self.subTest(product=product, api=api, kind=kind):
                        with tempfile.TemporaryDirectory() as temp_dir:
                            output = Path(temp_dir) / product / api / kind
                            row = cases.iloc[index].to_dict()
                            row.update(
                                out_dir=str(output),
                                save_vtp_on=int(save_artifacts),
                            )
                            if api == "run_case":
                                total = runner(row, lambda _message: None)
                                rows = [total, *total["component_rows"]]
                                self.assertTrue(
                                    all(
                                        list(item) == DIRECT_COMPONENT_KEYS
                                        for item in total["component_rows"]
                                    )
                                )
                                for item in total["component_rows"]:
                                    self.assertEqual(
                                        {
                                            "scope": str,
                                            "component_id": int,
                                            "component_stl_path": str,
                                            "CA": float,
                                            "CY": float,
                                            "CN": float,
                                            "Cl": float,
                                            "Cm": float,
                                            "Cn": float,
                                            "CD": float,
                                            "CL": float,
                                            "faces": int,
                                            "shielded_faces": int,
                                            "vtp_path": str,
                                        },
                                        {
                                            name: type(value)
                                            for name, value in item.items()
                                        },
                                    )
                            else:
                                result_frame = runner(
                                    pd.DataFrame([row]),
                                    lambda _message: None,
                                )
                                self.assertIn("case_id", result_frame.columns)
                                self.assertIn("solver_version", result_frame.columns)
                                self.assertIn("case_signature", result_frame.columns)
                                self.assertIn("run_started_at_utc", result_frame.columns)
                                self.assertIn("run_finished_at_utc", result_frame.columns)
                                rows = result_frame.to_dict(orient="records")

                            component_paths = (
                                row["stl_path"].split(";") if kind == "multi" else []
                            )
                            component_rows = rows[1:]
                            self.assertEqual(
                                ["total", *(["component"] * len(component_paths))],
                                [item["scope"] for item in rows],
                            )
                            self.assertEqual("", rows[0]["component_id"])
                            self.assertIs(type(rows[0]["component_id"]), str)
                            self.assertEqual("", rows[0]["component_stl_path"])
                            self.assertIs(type(rows[0]["component_stl_path"]), str)
                            self.assertEqual(
                                list(range(len(component_paths))),
                                [item["component_id"] for item in component_rows],
                            )
                            self.assertTrue(
                                all(
                                    type(item["component_id"]) is int
                                    for item in component_rows
                                )
                            )
                            self.assertEqual(
                                component_paths,
                                [item["component_stl_path"] for item in component_rows],
                            )
                            expected_vtp = (
                                str(output / f"{row['case_id']}.vtp")
                                if save_artifacts
                                else ""
                            )
                            self.assertEqual(expected_vtp, rows[0]["vtp_path"])
                            self.assertTrue(
                                all(item["vtp_path"] == "" for item in component_rows)
                            )
                            self.assertEqual(
                                save_artifacts,
                                (output / f"{row['case_id']}.vtp").is_file(),
                            )
                            self.assertEqual([], list(output.glob("*.npz")))

    def test_public_result_writers_keep_legacy_blank_and_integer_lexemes(self) -> None:
        inputs = pd.DataFrame([{"case_id": "lexical"}])
        results = pd.DataFrame(
            (
                {
                    "case_id": "lexical",
                    "scope": "total",
                    "component_id": "",
                    "component_stl_path": "",
                    "vtp_path": "",
                },
                {
                    "case_id": "lexical",
                    "scope": "component",
                    "component_id": 0,
                    "component_stl_path": "left.stl",
                    "vtp_path": "",
                },
                {
                    "case_id": "lexical",
                    "scope": "component",
                    "component_id": 1,
                    "component_stl_path": "right.stl",
                    "vtp_path": "",
                },
            )
        )
        for product, writer in (
            ("fmfsolver", write_fmf_results_csv),
            ("newtsolver", write_newt_results_csv),
        ):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as temp_dir:
                output = Path(temp_dir) / "results.csv"
                writer(str(output), inputs, results)
                with output.open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(["", "0", "1"], [r["component_id"] for r in rows])
                self.assertEqual(
                    ["", "left.stl", "right.stl"],
                    [r["component_stl_path"] for r in rows],
                )
                self.assertEqual(["", "", ""], [r["vtp_path"] for r in rows])

    def test_direct_result_normalization_does_not_mutate_neutral_projection(self) -> None:
        projection = CsvProjection(
            (
                "case_id",
                "scope",
                "component_id",
                "component_stl_path",
                "vtp_path",
                "CA",
            ),
            (
                {
                    "case_id": "neutral",
                    "scope": "total",
                    "component_id": None,
                    "component_stl_path": None,
                    "vtp_path": None,
                    "CA": 1.25,
                },
                {
                    "case_id": "neutral",
                    "scope": "component",
                    "component_id": 0,
                    "component_stl_path": "component.stl",
                    "vtp_path": None,
                    "CA": 0.25,
                },
            ),
        )
        before = tuple(tuple(row.items()) for row in projection.rows)

        frame = legacy_result_frame(projection, input_columns=())

        self.assertEqual(before, tuple(tuple(row.items()) for row in projection.rows))
        self.assertEqual(
            [
                {
                    "component_id": "",
                    "component_stl_path": "",
                    "vtp_path": "",
                },
                {
                    "component_id": 0,
                    "component_stl_path": "component.stl",
                    "vtp_path": "",
                },
            ],
            frame[
                ["component_id", "component_stl_path", "vtp_path"]
            ].to_dict(orient="records"),
        )
        self.assertIs(type(frame.iloc[1]["component_id"]), int)
        self.assertEqual([1.25, 0.25], frame["CA"].tolist())

    def test_atmosphere_tables_keep_legacy_return_shapes(self) -> None:
        table1, table2 = load_us1976_tables()
        self.assertEqual(list(table1.columns), ["Z", "T", "c"])
        self.assertEqual(list(table2.columns), ["Z", "V"])
        expected_temperature = sample_at_altitude_km(float(table1.iloc[0]["Z"]))[
            "T_K"
        ]
        table1.loc[:, "T"] = -1.0
        self.assertEqual(sample_at_altitude_km(0.0)["T_K"], expected_temperature)

    def test_direct_exporters_keep_exact_pinned_callable_contracts(self) -> None:
        signatures = {
            "export_vtp": (
                "(out_path: 'str', vertices: 'np.ndarray', faces: 'np.ndarray', "
                "cell_data: 'dict', field_data: 'dict | None' = None)"
            ),
        }
        for module in EXPORTER_MODULES:
            for name, signature in signatures.items():
                function = getattr(module, name)
                with self.subTest(module=module.__name__, function=name):
                    self.assertEqual(str(inspect.signature(function)), signature)
                    self.assertEqual(function.__name__, name)
                    self.assertEqual(function.__module__, module.__name__)
                    self.assertNotIn("return", function.__annotations__)
        self.assertIsNot(fmf_exporters.export_vtp, newt_exporters.export_vtp)

    def test_npz_public_symbols_are_absent(self) -> None:
        self.assertFalse(hasattr(fmfsolver.io, "export_npz"))
        self.assertFalse(hasattr(newtsolver.io, "export_npz"))
        self.assertFalse(hasattr(fmf_exporters, "export_npz"))
        self.assertFalse(hasattr(newt_exporters, "export_npz"))
        self.assertFalse(hasattr(panelsolver.core, "NpzProjection"))
        self.assertFalse(hasattr(panelsolver.core, "project_npz_artifact"))
        self.assertFalse(hasattr(panelsolver.app, "write_npz_projection"))

    def test_direct_exporters_keep_exact_semantic_artifacts_and_none_return(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            vertices = np.array(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                dtype=np.float32,
            )
            faces = np.array([[0, 1, 2]], dtype=np.int32)
            cell_data = {
                "panel_id": np.array([7], dtype=np.int16),
                "Cp_n": np.array([1.25], dtype=np.float32),
            }
            field_data = {
                "case_id": "direct",
                "component_ids": np.array([2, 4], dtype=np.int16),
            }
            for module in EXPORTER_MODULES:
                product = module.__name__.split(".", maxsplit=1)[0]
                vtp_path = output / product / "nested" / "direct.vtp"
                with self.subTest(product=product, artifact="vtp"):
                    result = module.export_vtp(
                        out_path=vtp_path,
                        vertices=vertices,
                        faces=faces,
                        cell_data=cell_data,
                        field_data=field_data,
                    )
                    self.assertIsNone(result)
                    poly = pv.read(vtp_path)
                    expected_points = vertices.astype(float)
                    expected_faces = np.array([3, 0, 1, 2], dtype=np.int64)
                    np.testing.assert_array_equal(poly.points, expected_points)
                    self.assertEqual(poly.points.dtype, expected_points.dtype)
                    np.testing.assert_array_equal(poly.faces, expected_faces)
                    self.assertEqual(poly.faces.dtype, expected_faces.dtype)
                    self.assertEqual(list(poly.cell_data), list(cell_data))
                    for name, expected in cell_data.items():
                        np.testing.assert_array_equal(poly.cell_data[name], expected)
                        self.assertEqual(poly.cell_data[name].dtype, expected.dtype)
                    self.assertEqual(list(poly.field_data), list(field_data))
                    for name, value in field_data.items():
                        expected = np.asarray([value])
                        np.testing.assert_array_equal(poly.field_data[name], expected)
                        self.assertEqual(poly.field_data[name].dtype, expected.dtype)


if __name__ == "__main__":
    unittest.main()
