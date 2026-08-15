from __future__ import annotations

import unittest

from panelsolver.app.environment import (
    resolve_parallel_chunk_environment,
    resolve_shielding_environment,
)
from panelsolver.core import SchedulerError, ShieldingConfig, ShieldingError


class EnvironmentResolutionTests(unittest.TestCase):
    def test_shielding_precedence_is_explicit_neutral_selected_legacy_default(self) -> None:
        environment = {
            "PANELSOLVER_SHIELD_BATCH_SIZE": "5",
            "FMFSOLVER_SHIELD_BATCH_SIZE": "3",
            "PANELSOLVER_SHIELD_CACHE_MAX": "0",
            "FMFSOLVER_SHIELD_CACHE_MAX": "7",
        }
        resolved = resolve_shielding_environment(
            ShieldingConfig(),
            legacy_env_prefix="FMFSOLVER",
            environment=environment,
        )
        self.assertEqual((5, 0), (resolved.batch_size, resolved.cache_max))

        explicit = resolve_shielding_environment(
            ShieldingConfig(batch_size=2, cache_max=9),
            legacy_env_prefix="FMFSOLVER",
            environment=environment,
        )
        self.assertEqual((2, 9), (explicit.batch_size, explicit.cache_max))

        legacy = resolve_shielding_environment(
            ShieldingConfig(),
            legacy_env_prefix="NEWTSOLVER",
            environment={
                "NEWTSOLVER_SHIELD_BATCH_SIZE": "6",
                "NEWTSOLVER_SHIELD_CACHE_MAX": "2",
            },
        )
        self.assertEqual((6, 2), (legacy.batch_size, legacy.cache_max))

        defaults = resolve_shielding_environment(
            ShieldingConfig(),
            legacy_env_prefix="FMFSOLVER",
            environment={},
        )
        self.assertIsNone(defaults.batch_size)
        self.assertIsNone(defaults.cache_max)

    def test_invalid_shielding_environment_names_the_boundary_variable(self) -> None:
        for name, value in (
            ("PANELSOLVER_SHIELD_BATCH_SIZE", "0"),
            ("PANELSOLVER_SHIELD_CACHE_MAX", "-1"),
            ("PANELSOLVER_SHIELD_CACHE_MAX", "bad"),
        ):
            with self.subTest(name=name, value=value), self.assertRaisesRegex(
                ShieldingError, name
            ):
                resolve_shielding_environment(
                    ShieldingConfig(),
                    legacy_env_prefix="FMFSOLVER",
                    environment={name: value},
                )

    def test_shielding_environment_is_ignored_when_shielding_is_disabled(self) -> None:
        config = ShieldingConfig(enabled=False)
        resolved = resolve_shielding_environment(
            config,
            legacy_env_prefix="FMFSOLVER",
            environment={"PANELSOLVER_SHIELD_BATCH_SIZE": "invalid"},
        )
        self.assertIs(config, resolved)

    def test_chunk_precedence_is_explicit_neutral_selected_legacy_default(self) -> None:
        environment = {
            "PANELSOLVER_PARALLEL_CHUNK_CASES": "3",
            "FMFSOLVER_PARALLEL_CHUNK_CASES": "4",
            "NEWTSOLVER_PARALLEL_CHUNK_CASES": "5",
        }
        self.assertEqual(
            2,
            resolve_parallel_chunk_environment(
                2,
                legacy_env_prefix="FMFSOLVER",
                environment=environment,
            ),
        )
        self.assertEqual(
            3,
            resolve_parallel_chunk_environment(
                legacy_env_prefix="FMFSOLVER",
                environment=environment,
            ),
        )
        self.assertEqual(
            4,
            resolve_parallel_chunk_environment(
                legacy_env_prefix="FMFSOLVER",
                environment={"FMFSOLVER_PARALLEL_CHUNK_CASES": "4"},
            ),
        )
        self.assertEqual(
            8,
            resolve_parallel_chunk_environment(
                legacy_env_prefix="FMFSOLVER",
                environment={"NEWTSOLVER_PARALLEL_CHUNK_CASES": "99"},
            ),
        )

    def test_invalid_chunk_environment_and_product_prefix_are_explicit(self) -> None:
        with self.assertRaisesRegex(SchedulerError, "PANELSOLVER"):
            resolve_parallel_chunk_environment(
                legacy_env_prefix="FMFSOLVER",
                environment={"PANELSOLVER_PARALLEL_CHUNK_CASES": "0"},
            )
        with self.assertRaisesRegex(ValueError, "legacy_env_prefix"):
            resolve_parallel_chunk_environment(
                legacy_env_prefix="UNKNOWN",
                environment={},
            )


if __name__ == "__main__":
    unittest.main()
