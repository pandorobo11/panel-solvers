from __future__ import annotations

import ast
import importlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pyvista as pv

import fmfsolver
import newtsolver
from fmfsolver.core.case_signature import build_case_signature as build_fmf_signature
from fmfsolver.core.sentman_core import sentman_dC_dA_vector
from fmfsolver.core.solver import run_case as run_fmf_case
from fmfsolver.io.exporters import export_npz, export_vtp
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from fmfsolver.physics.us1976 import load_us1976_tables, sample_at_altitude_km
from newtsolver.core.case_signature import build_case_signature as build_newt_signature
from newtsolver.core.panel_core import panel_force_density
from newtsolver.core.solver import run_case as run_newt_case
from newtsolver.io.io_cases import read_cases as read_newt_cases

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "phase1"
CONTRACTS = FIXTURES / "golden"

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

    def test_atmosphere_and_direct_serializers_keep_legacy_return_shapes(self) -> None:
        table1, table2 = load_us1976_tables()
        self.assertEqual(list(table1.columns), ["Z", "T", "c"])
        self.assertEqual(list(table2.columns), ["Z", "V"])
        expected_temperature = sample_at_altitude_km(float(table1.iloc[0]["Z"]))[
            "T_K"
        ]
        table1.loc[:, "T"] = -1.0
        self.assertEqual(sample_at_altitude_km(0.0)["T_K"], expected_temperature)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            vertices = np.array(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
            )
            faces = np.array([[0, 1, 2]], dtype=np.int64)
            export_vtp(
                output / "direct.vtp",
                vertices,
                faces,
                {"Cp_n": np.array([1.25])},
                {"case_id": "direct"},
            )
            export_npz(output / "direct.npz", Cp_n=np.array([1.25]))
            poly = pv.read(output / "direct.vtp")
            np.testing.assert_array_equal(poly.cell_data["Cp_n"], [1.25])
            with np.load(output / "direct.npz") as archive:
                np.testing.assert_array_equal(archive["Cp_n"], [1.25])


if __name__ == "__main__":
    unittest.main()
