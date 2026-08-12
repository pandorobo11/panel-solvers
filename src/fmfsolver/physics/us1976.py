# ruff: noqa: F821 - freeze pandas annotation text without importing it here
"""Pinned FMF atmosphere helpers owned by the shared Sentman model."""

from panelsolver.models.sentman_atmosphere import (
    altitude_range_km as _shared_altitude_range_km,
)
from panelsolver.models.sentman_atmosphere import (
    load_us1976_tables as _shared_load_us1976_tables,
)
from panelsolver.models.sentman_atmosphere import (
    mean_to_most_probable_speed as _shared_mean_to_most_probable_speed,
)
from panelsolver.models.sentman_atmosphere import (
    sample_at_altitude_km as _shared_sample_at_altitude_km,
)


def load_us1976_tables() -> "tuple[pd.DataFrame, pd.DataFrame]":
    """Return the shared pinned tables through the FMF callable identity."""
    return _shared_load_us1976_tables()


def altitude_range_km() -> "tuple[float, float]":
    """Return the shared pinned altitude range through the FMF identity."""
    return _shared_altitude_range_km()


def sample_at_altitude_km(alt_km: "float") -> "dict":
    """Delegate the pinned ``alt_km`` keyword to shared interpolation."""
    return _shared_sample_at_altitude_km(alt_km)


def mean_to_most_probable_speed(v_mean: "float") -> "float":
    """Delegate the pinned ``v_mean`` keyword to the shared conversion."""
    return _shared_mean_to_most_probable_speed(v_mean)

__all__ = (
    "altitude_range_km",
    "load_us1976_tables",
    "mean_to_most_probable_speed",
    "sample_at_altitude_km",
)
