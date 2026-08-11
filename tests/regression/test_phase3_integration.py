from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from panelsolver.core import (
    CommonCasePayload,
    LocalLoads,
    PanelGeometry,
    integrate_panel_loads,
)

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "phase1"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"
MANIFEST = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
COEFFICIENTS = ("CA", "CY", "CN", "Cl", "Cm", "Cn", "CD", "CL")


def _array(case: dict, name: str) -> np.ndarray:
    record = case["npz"]["arrays"][name]
    return np.asarray(record["values"], dtype=np.float64).reshape(record["shape"])


def _scalar(case: dict, name: str) -> float:
    return float(_array(case, name))


def _profile_tolerance(case: dict) -> tuple[float, float]:
    profile = MANIFEST["tolerance_profiles"][case["provenance"]["tolerance_profile"]]
    names = [profile["default"]]
    names.extend(item["tolerance"] for item in profile.get("path_overrides", []))
    tolerances = [MANIFEST["tolerances"][name] for name in names]
    return (
        max(item["atol"] for item in tolerances),
        max(item["rtol"] for item in tolerances),
    )


class Phase3IntegrationGoldenTests(unittest.TestCase):
    def test_all_phase1_force_and_moment_anchors_match(self) -> None:
        paths = sorted(GOLDEN_ROOT.glob("*/*.json"))
        paths = [path for path in paths if path.name != "contracts.json"]
        self.assertEqual(15, len(paths))

        for path in paths:
            with self.subTest(solver=path.parent.name, case_id=path.stem):
                golden = json.loads(path.read_text(encoding="utf-8"))
                normalized = golden["normalized_input"]
                geometry = PanelGeometry(
                    centers_stl_m=_array(golden, "centers_stl_m"),
                    normals_out_stl=_array(golden, "normals_out_stl"),
                    areas_m2=_array(golden, "areas_m2"),
                    component_ids=_array(golden, "face_stl_index").astype(np.int64),
                )
                golden_face_force = np.asarray(
                    golden["vtp"]["cell_data"]["C_face_stl"]["values"],
                    dtype=np.float64,
                )
                traction = golden_face_force * (
                    normalized["Aref_m2"] / geometry.areas_m2
                )[:, None]
                case = CommonCasePayload(
                    case_id=normalized["case_id"],
                    Aref_m2=normalized["Aref_m2"],
                    moment_reference_stl_m=[
                        normalized["ref_x_m"],
                        normalized["ref_y_m"],
                        normalized["ref_z_m"],
                    ],
                    Lref_Cl_m=normalized["Lref_Cl_m"],
                    Lref_Cm_m=normalized["Lref_Cm_m"],
                    Lref_Cn_m=normalized["Lref_Cn_m"],
                    alpha_t_deg=_scalar(golden, "alpha_t_deg_resolved"),
                    beta_t_deg=_scalar(golden, "beta_t_deg_resolved"),
                )

                result = integrate_panel_loads(geometry, LocalLoads(traction), case)
                atol, rtol = _profile_tolerance(golden)

                np.testing.assert_allclose(
                    result.face_force_coeff_stl,
                    golden_face_force,
                    rtol=0.0,
                    atol=1.0e-12,
                )
                np.testing.assert_allclose(
                    result.total.force_coeff_stl,
                    _array(golden, "C_force_stl"),
                    rtol=rtol,
                    atol=atol,
                )
                np.testing.assert_allclose(
                    result.total.force_coeff_body,
                    _array(golden, "C_force_body"),
                    rtol=rtol,
                    atol=atol,
                )
                np.testing.assert_allclose(
                    result.total.moment_area_coeff_body_m,
                    _array(golden, "C_M_body"),
                    rtol=rtol,
                    atol=atol,
                )
                for coefficient in COEFFICIENTS:
                    self.assertTrue(
                        np.isclose(
                            getattr(result.total, coefficient),
                            _scalar(golden, coefficient),
                            rtol=rtol,
                            atol=atol,
                        ),
                        coefficient,
                    )

                shielded = _array(golden, "shielded").astype(bool)
                if shielded.any():
                    np.testing.assert_array_equal(
                        result.face_force_coeff_stl[shielded],
                        np.zeros((int(shielded.sum()), 3)),
                    )


if __name__ == "__main__":
    unittest.main()
