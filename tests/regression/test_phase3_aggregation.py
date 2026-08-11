from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from panelsolver.core import (
    CommonCasePayload,
    LocalLoads,
    ModelCasePayload,
    PanelFlowState,
    PanelGeometry,
    assemble_common_results,
)

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "phase1"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"
MANIFEST = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
COEFFICIENTS = ("CA", "CY", "CN", "Cl", "Cm", "Cn", "CD", "CL")
MULTICOMPONENT_CASES = (
    ("fmfsolver", "fmf_bank_multicomponent"),
    ("newtsolver", "newt_bank_multicomponent"),
)


def _array(golden: dict, name: str) -> np.ndarray:
    record = golden["npz"]["arrays"][name]
    return np.asarray(record["values"], dtype=np.float64).reshape(record["shape"])


def _scalar(golden: dict, name: str) -> float:
    return float(_array(golden, name))


def _tolerance(golden: dict) -> tuple[float, float]:
    profile = MANIFEST["tolerance_profiles"][golden["provenance"]["tolerance_profile"]]
    names = [profile["default"]]
    names.extend(item["tolerance"] for item in profile.get("path_overrides", []))
    values = [MANIFEST["tolerances"][name] for name in names]
    return max(v["atol"] for v in values), max(v["rtol"] for v in values)


class Phase3ComponentGoldenTests(unittest.TestCase):
    def test_multicomponent_rows_and_totals_match_both_products(self) -> None:
        for solver, case_id in MULTICOMPONENT_CASES:
            with self.subTest(solver=solver, case_id=case_id):
                golden = json.loads(
                    (GOLDEN_ROOT / solver / f"{case_id}.json").read_text(
                        encoding="utf-8"
                    )
                )
                normalized = golden["normalized_input"]
                areas = _array(golden, "areas_m2")
                face_force = np.asarray(
                    golden["vtp"]["cell_data"]["C_face_stl"]["values"],
                    dtype=np.float64,
                )
                geometry = PanelGeometry(
                    centers_stl_m=_array(golden, "centers_stl_m"),
                    normals_out_stl=_array(golden, "normals_out_stl"),
                    areas_m2=areas,
                    component_ids=_array(golden, "face_stl_index").astype(np.int64),
                )
                common_case = CommonCasePayload(
                    case_id=case_id,
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
                results = assemble_common_results(
                    common_case,
                    ModelCasePayload(solver),
                    geometry,
                    PanelFlowState(
                        _array(golden, "Vhat_stl"),
                        _array(golden, "shielded").astype(bool),
                    ),
                    LocalLoads(face_force * (normalized["Aref_m2"] / areas)[:, None]),
                )
                component_rows = [
                    row for row in golden["csv"]["rows"] if row["scope"] == "component"
                ]
                atol, rtol = _tolerance(golden)

                self.assertEqual(
                    [row["component_id"] for row in component_rows],
                    [item.component_id for item in results.components],
                )
                for expected, actual in zip(
                    component_rows,
                    results.components,
                    strict=True,
                ):
                    self.assertEqual(expected["faces"], actual.face_count)
                    self.assertEqual(
                        expected["shielded_faces"],
                        actual.shielded_face_count,
                    )
                    for coefficient in COEFFICIENTS:
                        self.assertTrue(
                            np.isclose(
                                expected[coefficient],
                                getattr(actual.integrated, coefficient),
                                atol=atol,
                                rtol=rtol,
                            ),
                            coefficient,
                        )

                for coefficient in COEFFICIENTS:
                    component_sum = sum(
                        getattr(item.integrated, coefficient)
                        for item in results.components
                    )
                    self.assertTrue(
                        np.isclose(
                            getattr(results.total, coefficient),
                            component_sum,
                            atol=atol,
                            rtol=rtol,
                        )
                    )


if __name__ == "__main__":
    unittest.main()
