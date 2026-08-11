import unittest

import numpy as np

from panelsolver.core import (
    ContractValueError,
    NonFiniteError,
    ShapeError,
    body_to_stability,
    stl_to_body,
    velocity_hat_stl_from_tangent_angles,
)


class ResolvedAttitudeTests(unittest.TestCase):
    def test_zero_tangent_angles_point_along_positive_stl_x(self) -> None:
        np.testing.assert_array_equal(
            np.array([1.0, 0.0, 0.0]),
            velocity_hat_stl_from_tangent_angles(0.0, 0.0),
        )

    def test_signs_and_unit_length_follow_tangent_convention(self) -> None:
        velocity = velocity_hat_stl_from_tangent_angles(30.0, 20.0)
        self.assertGreater(velocity[0], 0.0)
        self.assertLess(velocity[1], 0.0)
        self.assertGreater(velocity[2], 0.0)
        self.assertAlmostEqual(1.0, float(np.linalg.norm(velocity)), places=15)

    def test_resolved_angles_do_not_apply_a_product_input_domain(self) -> None:
        velocity = velocity_hat_stl_from_tangent_angles(100.0, 0.0)
        self.assertLess(velocity[0], 0.0)
        self.assertGreater(velocity[2], 0.0)
        self.assertAlmostEqual(1.0, float(np.linalg.norm(velocity)), places=15)

    def test_angles_reject_booleans_and_nonfinite_values(self) -> None:
        with self.assertRaises(ContractValueError):
            velocity_hat_stl_from_tangent_angles(True, 0.0)
        with self.assertRaises(NonFiniteError):
            velocity_hat_stl_from_tangent_angles(0.0, np.inf)
        with self.assertRaises(NonFiniteError):
            body_to_stability([1.0, 0.0, 0.0], alpha_t_deg=np.nan)


class FrameTransformTests(unittest.TestCase):
    def test_stl_to_body_preserves_arbitrary_leading_dimensions(self) -> None:
        vectors_stl = np.arange(24, dtype=np.float32).reshape(2, 4, 3)
        original = vectors_stl.copy()

        vectors_body = stl_to_body(vectors_stl)

        np.testing.assert_array_equal(
            vectors_body,
            original * np.array([-1.0, 1.0, -1.0]),
        )
        np.testing.assert_array_equal(vectors_stl, original)
        self.assertEqual(vectors_stl.shape, vectors_body.shape)
        self.assertEqual(np.dtype(np.float64), vectors_body.dtype)
        self.assertTrue(vectors_body.flags.c_contiguous)

    def test_stl_to_body_is_its_own_inverse(self) -> None:
        vectors = np.array([[1.0, 2.0, 3.0], [-4.0, 5.0, -6.0]])
        np.testing.assert_array_equal(vectors, stl_to_body(stl_to_body(vectors)))

    def test_body_to_stability_uses_positive_y_rotation(self) -> None:
        transformed = body_to_stability(
            np.array([1.0, 2.0, 3.0]),
            alpha_t_deg=90.0,
        )
        np.testing.assert_allclose(
            np.array([3.0, 2.0, -1.0]),
            transformed,
            rtol=0.0,
            atol=1.0e-15,
        )

    def test_vector_transforms_reject_invalid_shape_dtype_and_values(self) -> None:
        for value in (1.0, [1.0, 2.0], np.zeros((2, 3, 4))):
            with self.subTest(value=np.shape(value)):
                with self.assertRaises(ShapeError):
                    stl_to_body(value)
        with self.assertRaises(ContractValueError):
            stl_to_body([True, False, True])
        with self.assertRaises(ContractValueError):
            body_to_stability(["1", "2", "3"], alpha_t_deg=0.0)
        with self.assertRaises(ContractValueError):
            stl_to_body([[1.0, 2.0, 3.0], [4.0, 5.0]])
        with self.assertRaises(NonFiniteError):
            body_to_stability([1.0, np.nan, 3.0], alpha_t_deg=0.0)


if __name__ == "__main__":
    unittest.main()
