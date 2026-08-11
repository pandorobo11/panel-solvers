from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from panelsolver.core import (
    body_to_stability,
    stl_to_body,
    velocity_hat_stl_from_tangent_angles,
)

GOLDEN_ROOT = Path(__file__).parents[1] / "fixtures" / "phase1" / "golden"
GEOMETRY_ATTITUDE_ATOL = 1.0e-12


def _array(case: dict, name: str) -> np.ndarray:
    record = case["npz"]["arrays"][name]
    return np.asarray(record["values"], dtype=np.float64).reshape(record["shape"])


def _scalar(case: dict, name: str) -> float:
    return float(_array(case, name))


class Phase3FrameGoldenTests(unittest.TestCase):
    def test_all_phase1_attitude_and_frame_anchors_match(self) -> None:
        paths = sorted(GOLDEN_ROOT.glob("*/*.json"))
        paths = [path for path in paths if path.name != "contracts.json"]
        self.assertEqual(15, len(paths))

        for path in paths:
            with self.subTest(solver=path.parent.name, case_id=path.stem):
                case = json.loads(path.read_text(encoding="utf-8"))
                alpha_t_deg = _scalar(case, "alpha_t_deg_resolved")
                beta_t_deg = _scalar(case, "beta_t_deg_resolved")

                np.testing.assert_allclose(
                    _array(case, "Vhat_stl"),
                    velocity_hat_stl_from_tangent_angles(
                        alpha_t_deg,
                        beta_t_deg,
                    ),
                    rtol=0.0,
                    atol=GEOMETRY_ATTITUDE_ATOL,
                )

                force_body = stl_to_body(_array(case, "C_force_stl"))
                np.testing.assert_array_equal(
                    _array(case, "C_force_body"),
                    force_body,
                )

                force_stability = body_to_stability(
                    force_body,
                    alpha_t_deg=alpha_t_deg,
                )
                np.testing.assert_allclose(
                    np.array([_scalar(case, "CD"), _scalar(case, "CL")]),
                    -force_stability[[0, 2]],
                    rtol=0.0,
                    atol=GEOMETRY_ATTITUDE_ATOL,
                )


if __name__ == "__main__":
    unittest.main()
