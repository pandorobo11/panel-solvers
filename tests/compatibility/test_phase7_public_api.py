from __future__ import annotations

import ast
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
import fmfsolver.io.exporters as fmf_exporters
import newtsolver
import newtsolver.io.exporters as newt_exporters
from fmfsolver.core.case_signature import build_case_signature as build_fmf_signature
from fmfsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_fmf_case_results_parallel,
)
from fmfsolver.core.sentman_core import sentman_dC_dA_vector
from fmfsolver.core.solver import run_case as run_fmf_case
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from fmfsolver.physics.us1976 import load_us1976_tables, sample_at_altitude_km
from newtsolver.core.case_signature import build_case_signature as build_newt_signature
from newtsolver.core.panel_core import panel_force_density
from newtsolver.core.parallel_scheduler import (
    iter_case_results_parallel as iter_newt_case_results_parallel,
)
from newtsolver.core.solver import run_case as run_newt_case
from newtsolver.io.io_cases import read_cases as read_newt_cases

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "phase1"
CONTRACTS = FIXTURES / "golden"
EXPORTER_MODULES = (fmf_exporters, newt_exporters)

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
            row = reader(FIXTURES / "inputs" / filename).iloc[0].to_dict()
            row.update(save_vtp_on=0, save_npz_on=0)
            result = runner(row, lambda _message: None)
            with self.subTest(case_id=row["case_id"]):
                self.assertEqual(result["case_signature"], signature(row))
                self.assertEqual(result["scope"], "total")
                self.assertEqual(result["component_rows"], [])
                self.assertAlmostEqual(result["CA"], expected_ca, places=14)

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
            "export_npz": "(out_path: 'str', **arrays)",
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
        self.assertIsNot(fmf_exporters.export_npz, newt_exporters.export_npz)

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
            npz_arrays = {
                "panel_id": np.array([7], dtype=np.int16),
                "loads": np.array([[1.25, -0.5, 0.0]], dtype=np.float32),
            }

            for module in EXPORTER_MODULES:
                product = module.__name__.split(".", maxsplit=1)[0]
                vtp_path = output / product / "nested" / "direct.vtp"
                npz_path = output / product / "nested" / "direct.npz"
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

                with self.subTest(product=product, artifact="npz"):
                    result = module.export_npz(out_path=npz_path, **npz_arrays)
                    self.assertIsNone(result)
                    with np.load(npz_path) as archive:
                        self.assertEqual(archive.files, list(npz_arrays))
                        for name, expected in npz_arrays.items():
                            np.testing.assert_array_equal(archive[name], expected)
                            self.assertEqual(archive[name].dtype, expected.dtype)


if __name__ == "__main__":
    unittest.main()
