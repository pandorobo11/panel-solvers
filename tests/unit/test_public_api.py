from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

import panelsolver
from fmfsolver.case_adapter import adapt_row as adapt_fmf_row
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from newtsolver.case_adapter import adapt_row as adapt_hypersonic_row
from newtsolver.io.io_cases import read_cases as read_hypersonic_cases
from panelsolver import (
    HypersonicCase,
    SentmanCase,
    SolveResult,
    resolve_attitude,
    solve_hypersonic,
    solve_sentman,
)
from panelsolver.core import execute_case
from tests.current_case_fixtures import read_current_cases

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"


def _paths(row) -> tuple[str, ...]:
    return tuple(part.strip() for part in row["stl_path"].split(";") if part.strip())


def _common(row) -> dict[str, object]:
    return {
        "case_id": row["case_id"],
        "stl_paths": _paths(row),
        "stl_scale_m_per_unit": row["stl_scale_m_per_unit"],
        "attitude": resolve_attitude(
            row["alpha_deg"],
            row["beta_or_bank_deg"],
            row["attitude_input"],
        ),
        "Aref_m2": row["Aref_m2"],
        "moment_reference_stl_m": (
            row["ref_x_m"],
            row["ref_y_m"],
            row["ref_z_m"],
        ),
        "Lref_Cl_m": row["Lref_Cl_m"],
        "Lref_Cm_m": row["Lref_Cm_m"],
        "Lref_Cn_m": row["Lref_Cn_m"],
        "shielding": bool(row["shielding_on"]),
        "ray_backend": row["ray_backend"],
    }


class PublicApiTests(unittest.TestCase):
    def test_package_root_has_one_small_explicit_stable_surface(self) -> None:
        self.assertEqual(
            (
                "HypersonicCase",
                "ResolvedAttitude",
                "SentmanCase",
                "SolveResult",
                "resolve_attitude",
                "solve_hypersonic",
                "solve_sentman",
            ),
            panelsolver.__all__,
        )
        self.assertNotEqual(SentmanCase, HypersonicCase)
        self.assertFalse(hasattr(panelsolver, "CaseExecutionRequest"))
        self.assertFalse(hasattr(panelsolver, "ProductRuntimePolicy"))

    def test_sentman_solve_is_in_memory_and_matches_compatibility_path(self) -> None:
        row = read_current_cases(
            read_fmf_cases,
            INPUTS / "fmfsolver_cases.csv",
        ).iloc[0].to_dict()
        case = SentmanCase(
            **_common(row),
            speed_ratio=row["S"],
            translational_temperature_k=row["Ti_K"],
            wall_temperature_k=row["Tw_K"],
        )
        compatibility = execute_case(adapt_fmf_row(row).request)
        with tempfile.TemporaryDirectory() as temporary:
            original = os.getcwd()
            os.chdir(temporary)
            try:
                result = solve_sentman(case)
            finally:
                os.chdir(original)
            self.assertEqual([], list(Path(temporary).iterdir()))
        self.assertIsInstance(result, SolveResult)
        np.testing.assert_array_equal(
            compatibility.results.total.force_coeff_stl,
            result.coefficients.force_coeff_stl,
        )
        np.testing.assert_array_equal(
            compatibility.results.local_loads.traction_coeff_stl,
            result.local_loads.traction_coeff_stl,
        )
        self.assertEqual(compatibility.signature.digest, result.case_signature)

    def test_hypersonic_solve_is_in_memory_and_matches_compatibility_path(self) -> None:
        row = read_current_cases(
            read_hypersonic_cases,
            INPUTS / "newtsolver_cases.csv",
        ).iloc[0].to_dict()
        case = HypersonicCase(
            **_common(row),
            mach=row["Mach"],
            gamma=row["gamma"],
            windward_equation=row["windward_eq"],
            leeward_equation=row["leeward_eq"],
        )
        compatibility = execute_case(adapt_hypersonic_row(row).request)
        with tempfile.TemporaryDirectory() as temporary:
            original = os.getcwd()
            os.chdir(temporary)
            try:
                result = solve_hypersonic(case)
            finally:
                os.chdir(original)
            self.assertEqual([], list(Path(temporary).iterdir()))
        self.assertIsInstance(result, SolveResult)
        np.testing.assert_array_equal(
            compatibility.results.total.force_coeff_stl,
            result.coefficients.force_coeff_stl,
        )
        np.testing.assert_array_equal(
            compatibility.results.local_loads.traction_coeff_stl,
            result.local_loads.traction_coeff_stl,
        )
        self.assertEqual(compatibility.signature.digest, result.case_signature)


if __name__ == "__main__":
    unittest.main()
