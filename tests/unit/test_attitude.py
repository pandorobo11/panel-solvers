from __future__ import annotations

import unittest

import numpy as np

from panelsolver.app.attitude import ResolvedAttitude


class ResolvedAttitudeInvariantTests(unittest.TestCase):
    def test_direct_construction_normalizes_and_freezes_finite_vectors(self) -> None:
        attitude = ResolvedAttitude(
            velocity_hat_stl=np.array([3.0, 4.0, 0.0]),
            alpha_t_deg="10.5",
            beta_t_deg=-20,
            input_mode="BETA_TAN",
        )

        np.testing.assert_array_equal(attitude.velocity_hat_stl, [0.6, 0.8, 0.0])
        self.assertFalse(attitude.velocity_hat_stl.flags.writeable)
        self.assertEqual(10.5, attitude.alpha_t_deg)
        self.assertEqual(-20.0, attitude.beta_t_deg)
        self.assertEqual("beta_tan", attitude.input_mode)

    def test_direct_construction_normalizes_extreme_finite_vector(self) -> None:
        attitude = ResolvedAttitude(
            velocity_hat_stl=np.array([1.0e308, 1.0e308, 1.0e308]),
            alpha_t_deg=0.0,
            beta_t_deg=0.0,
            input_mode="bank",
        )

        expected = np.full(3, 1.0 / np.sqrt(3.0))
        np.testing.assert_allclose(
            attitude.velocity_hat_stl,
            expected,
            rtol=0.0,
            atol=1.0e-15,
        )
        self.assertAlmostEqual(
            1.0,
            float(np.linalg.norm(attitude.velocity_hat_stl)),
            places=15,
        )

    def test_direct_construction_rejects_invalid_angles(self) -> None:
        for field in ("alpha_t_deg", "beta_t_deg"):
            for value in (True, np.bool_(False), np.nan, np.inf, -np.inf):
                kwargs = {
                    "velocity_hat_stl": [1.0, 0.0, 0.0],
                    "alpha_t_deg": 0.0,
                    "beta_t_deg": 0.0,
                    "input_mode": "beta_tan",
                    field: value,
                }
                with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    ValueError, field
                ):
                    ResolvedAttitude(**kwargs)

    def test_direct_construction_rejects_invalid_vectors(self) -> None:
        invalid = (
            [0.0, 0.0, 0.0],
            [1.0, 0.0],
            [np.nan, 0.0, 0.0],
            [np.inf, 0.0, 0.0],
        )
        for velocity in invalid:
            with self.subTest(velocity=velocity), self.assertRaises(ValueError):
                ResolvedAttitude(velocity, 0.0, 0.0, "beta_tan")


if __name__ == "__main__":
    unittest.main()
