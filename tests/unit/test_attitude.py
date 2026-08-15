from __future__ import annotations

import unittest

import numpy as np

from panelsolver.app.attitude import ResolvedAttitude, resolve_attitude


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
        self.assertIsInstance(attitude.velocity_hat_stl.base, bytes)
        self.assertEqual(10.5, attitude.alpha_t_deg)
        self.assertEqual(-20.0, attitude.beta_t_deg)
        self.assertEqual("beta_tan", attitude.input_mode)

    def test_direct_construction_accepts_integer_vector(self) -> None:
        attitude = ResolvedAttitude([1, 0, 0], 0.0, 0.0, "beta_tan")

        np.testing.assert_array_equal(attitude.velocity_hat_stl, [1.0, 0.0, 0.0])
        self.assertEqual(np.dtype(np.float64), attitude.velocity_hat_stl.dtype)
        self.assertFalse(attitude.velocity_hat_stl.flags.writeable)
        self.assertIsInstance(attitude.velocity_hat_stl.base, bytes)

    def test_direct_construction_normalizes_extreme_finite_vectors(self) -> None:
        maximum = np.finfo(np.float64).max
        vectors = (
            [1.0e308, 1.0e308, 1.0e308],
            [1.2e308, 1.2e308, 1.2e308],
            [maximum, maximum, maximum],
            [maximum, 1.0, -maximum / 2.0],
        )
        for velocity in vectors:
            with self.subTest(velocity=velocity):
                attitude = ResolvedAttitude(
                    velocity_hat_stl=velocity,
                    alpha_t_deg=0.0,
                    beta_t_deg=0.0,
                    input_mode="bank",
                )
                self.assertTrue(np.isfinite(attitude.velocity_hat_stl).all())
                self.assertAlmostEqual(
                    1.0,
                    float(np.linalg.norm(attitude.velocity_hat_stl)),
                    places=15,
                )
                self.assertFalse(attitude.velocity_hat_stl.flags.writeable)
                self.assertIsInstance(attitude.velocity_hat_stl.base, bytes)

        expected = np.full(3, 1.0 / np.sqrt(3.0))
        np.testing.assert_allclose(
            ResolvedAttitude(vectors[0], 0.0, 0.0, "bank").velocity_hat_stl,
            expected,
            rtol=0.0,
            atol=1.0e-15,
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
            [True, False, False],
            np.array([True, False, False], dtype=np.bool_),
            np.array([1.0, 0.0, 0.0], dtype=np.complex128),
            np.array([1.0, 0.0, 0.0], dtype=object),
            np.array(["1", "0", "0"]),
            [[1.0], [0.0, 0.0]],
            [0.0, 0.0, 0.0],
            [1.0, 0.0],
            [np.nan, 0.0, 0.0],
            [np.inf, 0.0, 0.0],
        )
        for velocity in invalid:
            with self.subTest(velocity=repr(velocity)), self.assertRaisesRegex(
                ValueError, "velocity_hat_stl"
            ):
                ResolvedAttitude(velocity, 0.0, 0.0, "beta_tan")

    def test_resolve_attitude_rejects_boolean_angles_before_float_conversion(
        self,
    ) -> None:
        for alpha, beta in ((True, 0.0), (np.bool_(False), 0.0), (0.0, True)):
            with self.subTest(alpha=alpha, beta=beta), self.assertRaisesRegex(
                ValueError, "finite real"
            ):
                resolve_attitude(
                    alpha,
                    beta,
                    "beta_tan",
                )

    def test_beta_tan_uses_one_canonical_principal_domain(self) -> None:
        for alpha, beta in ((-90.0, 0.0), (90.0, 0.0), (0.0, -90.0), (0.0, 90.0)):
            with self.subTest(alpha=alpha, beta=beta), self.assertRaisesRegex(
                ValueError, "strictly between -90 and 90"
            ):
                resolve_attitude(alpha, beta, "beta_tan")


if __name__ == "__main__":
    unittest.main()
