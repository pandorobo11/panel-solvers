"""Application-boundary resolution of neutral and compatibility settings."""

from __future__ import annotations

import os
from collections.abc import Mapping

from panelsolver.core import (
    SchedulerError,
    ShieldingConfig,
    ShieldingError,
    resolve_parallel_chunk_cases,
)

_LEGACY_ENV_PREFIXES = frozenset({"FMFSOLVER", "NEWTSOLVER"})


def _validated_legacy_prefix(value: str) -> str:
    if value not in _LEGACY_ENV_PREFIXES:
        raise ValueError("legacy_env_prefix is invalid")
    return value


def _environment_value(
    suffix: str,
    legacy_env_prefix: str,
    environment: Mapping[str, str] | None,
) -> tuple[str, str] | None:
    values = os.environ if environment is None else environment
    for name in (
        f"PANELSOLVER_{suffix}",
        f"{legacy_env_prefix}_{suffix}",
    ):
        raw = str(values.get(name, "")).strip()
        if raw:
            return name, raw
    return None


def _shielding_environment_integer(
    suffix: str,
    legacy_env_prefix: str,
    environment: Mapping[str, str] | None,
    *,
    minimum: int,
) -> int | None:
    found = _environment_value(suffix, legacy_env_prefix, environment)
    if found is None:
        return None
    name, raw = found
    try:
        parsed = int(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ShieldingError(f"{name} must be an integer >= {minimum}.") from exc
    if parsed < minimum:
        raise ShieldingError(f"{name} must be an integer >= {minimum}.")
    return parsed


def resolve_shielding_environment(
    config: ShieldingConfig,
    *,
    legacy_env_prefix: str,
    environment: Mapping[str, str] | None = None,
) -> ShieldingConfig:
    """Resolve explicit > neutral > selected compatibility environment values."""
    if not isinstance(config, ShieldingConfig):
        raise TypeError("config must be a ShieldingConfig instance")
    prefix = _validated_legacy_prefix(legacy_env_prefix)
    if not config.enabled:
        return config
    batch_size = config.batch_size
    if batch_size is None:
        batch_size = _shielding_environment_integer(
            "SHIELD_BATCH_SIZE",
            prefix,
            environment,
            minimum=1,
        )
    return ShieldingConfig(
        enabled=config.enabled,
        ray_backend=config.ray_backend,
        batch_size=batch_size,
    )


def resolve_parallel_chunk_environment(
    chunk_cases: int | None = None,
    *,
    legacy_env_prefix: str,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Resolve one product's chunk setting before entering the core scheduler."""
    prefix = _validated_legacy_prefix(legacy_env_prefix)
    if chunk_cases is not None:
        return resolve_parallel_chunk_cases(chunk_cases)
    found = _environment_value(
        "PARALLEL_CHUNK_CASES",
        prefix,
        environment,
    )
    if found is None:
        return resolve_parallel_chunk_cases()
    name, raw = found
    try:
        return resolve_parallel_chunk_cases(raw)
    except SchedulerError as exc:
        raise SchedulerError(f"{name} must be an integer >= 1.") from exc


__all__ = (
    "resolve_parallel_chunk_environment",
    "resolve_shielding_environment",
)
