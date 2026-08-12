from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import numpy as np
from trimesh.ray import has_embree

from panelsolver.core import (
    RayBackend,
    ShieldingConfig,
    ShieldingError,
    clear_mesh_cache,
    clear_shielding_cache,
    compute_shielding,
    load_panel_mesh,
    shielding_cache_stats,
)

from .test_mesh_loading import FIXTURE_STL


class _CountingIntersector:
    def __init__(self) -> None:
        self.call_count = 0

    def intersects_id(self, **_kwargs):
        self.call_count += 1
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)


class ShieldingTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_mesh_cache()
        clear_shielding_cache()
        self.mesh = load_panel_mesh([FIXTURE_STL / "cube.stl"], 1.0).mesh

    def test_disabled_shielding_is_exact_zero_and_not_used(self) -> None:
        result = compute_shielding(
            self.mesh,
            np.array([1.0, 0.0, 0.0]),
            ShieldingConfig(enabled=False, ray_backend="embree"),
        )
        np.testing.assert_array_equal(result.shielded, np.zeros(12, dtype=bool))
        self.assertFalse(result.shielded.flags.writeable)
        self.assertEqual("embree", result.config.requested_backend)
        self.assertEqual("not_used", result.config.effective_backend)
        self.assertEqual(0, shielding_cache_stats().intersector_entries)

    def test_cache_key_includes_direction_batch_backend_and_geometry(self) -> None:
        intersector = _CountingIntersector()
        with patch(
            "panelsolver.core.shielding._resolve_intersector",
            return_value=(intersector, "rtree"),
        ):
            first = compute_shielding(
                self.mesh,
                np.array([1.0, 0.0, 0.0]),
                ShieldingConfig(batch_size=8, cache_max=4),
            )
            second = compute_shielding(
                self.mesh,
                np.array([1.0, 0.0, 0.0]),
                ShieldingConfig(batch_size=8, cache_max=4),
            )
            compute_shielding(
                self.mesh,
                np.array([0.0, 1.0, 0.0]),
                ShieldingConfig(batch_size=8, cache_max=4),
            )
            compute_shielding(
                self.mesh,
                np.array([1.0, 0.0, 0.0]),
                ShieldingConfig(batch_size=3, cache_max=4),
            )

        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        expected_calls = 2 + 2 + 4
        self.assertEqual(expected_calls, intersector.call_count)
        self.assertEqual(1, shielding_cache_stats().mask_hits)

    def test_cached_mask_cannot_be_mutated(self) -> None:
        first = compute_shielding(
            self.mesh,
            np.array([1.0, 0.0, 0.0]),
            ShieldingConfig(ray_backend="rtree"),
        )
        with self.assertRaises(ValueError):
            first.shielded[0] = not first.shielded[0]
        second = compute_shielding(
            self.mesh,
            np.array([1.0, 0.0, 0.0]),
            ShieldingConfig(ray_backend="rtree"),
        )
        np.testing.assert_array_equal(first.shielded, second.shielded)

    def test_neutral_environment_precedes_selected_legacy_prefix(self) -> None:
        intersector = _CountingIntersector()
        environment = {
            "PANELSOLVER_SHIELD_BATCH_SIZE": "5",
            "FMFSOLVER_SHIELD_BATCH_SIZE": "3",
            "PANELSOLVER_SHIELD_CACHE_MAX": "0",
            "FMFSOLVER_SHIELD_CACHE_MAX": "7",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(
                "panelsolver.core.shielding._resolve_intersector",
                return_value=(intersector, "rtree"),
            ),
        ):
            result = compute_shielding(
                self.mesh,
                np.array([1.0, 0.0, 0.0]),
                ShieldingConfig(legacy_env_prefix="FMFSOLVER"),
            )
        self.assertEqual(5, result.config.batch_size)
        self.assertEqual(0, result.config.cache_max)

    def test_legacy_fallback_and_invalid_environment_are_explicit(self) -> None:
        intersector = _CountingIntersector()
        with (
            patch.dict(
                os.environ,
                {
                    "NEWTSOLVER_SHIELD_BATCH_SIZE": "6",
                    "NEWTSOLVER_SHIELD_CACHE_MAX": "2",
                },
                clear=True,
            ),
            patch(
                "panelsolver.core.shielding._resolve_intersector",
                return_value=(intersector, "rtree"),
            ),
        ):
            result = compute_shielding(
                self.mesh,
                np.array([1.0, 0.0, 0.0]),
                ShieldingConfig(legacy_env_prefix="NEWTSOLVER"),
            )
        self.assertEqual((6, 2), (result.config.batch_size, result.config.cache_max))

        for name, value in (
            ("PANELSOLVER_SHIELD_BATCH_SIZE", "0"),
            ("PANELSOLVER_SHIELD_CACHE_MAX", "-1"),
            ("PANELSOLVER_SHIELD_CACHE_MAX", "bad"),
        ):
            with self.subTest(name=name, value=value):
                clear_shielding_cache()
                with patch.dict(os.environ, {name: value}, clear=True):
                    with self.assertRaisesRegex(ShieldingError, name):
                        compute_shielding(
                            self.mesh,
                            np.array([1.0, 0.0, 0.0]),
                            ShieldingConfig(ray_backend="rtree"),
                        )

    def test_explicit_unavailable_embree_does_not_fallback(self) -> None:
        with (
            patch("panelsolver.core.shielding.has_embree", False),
            patch("panelsolver.core.shielding._ray_pyembree", None),
        ):
            with self.assertRaisesRegex(ShieldingError, "not available"):
                compute_shielding(
                    self.mesh,
                    np.array([1.0, 0.0, 0.0]),
                    ShieldingConfig(ray_backend=RayBackend.EMBREE),
                )

    def test_auto_reports_the_effective_trimesh_backend(self) -> None:
        result = compute_shielding(
            self.mesh,
            np.array([1.0, 0.0, 0.0]),
            ShieldingConfig(ray_backend="auto", cache_max=0),
        )
        expected = "embree" if has_embree else "rtree"
        self.assertEqual("auto", result.config.requested_backend)
        self.assertEqual(expected, result.config.effective_backend)

    def test_rejects_invalid_direction_and_configuration(self) -> None:
        invalid_directions = (
            np.array([0.0, 0.0, 0.0]),
            np.array([1.0, 0.0]),
            np.array([np.nan, 0.0, 0.0]),
            np.array(["x", "y", "z"]),
        )
        for direction in invalid_directions:
            with self.subTest(direction=direction):
                with self.assertRaises(ShieldingError):
                    compute_shielding(self.mesh, direction)

        for kwargs in (
            {"batch_size": 0},
            {"cache_max": -1},
            {"ray_backend": "bad"},
            {"legacy_env_prefix": "OTHER"},
            {"enabled": 1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ShieldingError):
                    ShieldingConfig(**kwargs)


if __name__ == "__main__":
    unittest.main()
