"""US1976 atmosphere sampling owned by the Sentman physical model."""

from __future__ import annotations

import math

import numpy as np

from ._sentman_atmosphere_data import (
    ALTITUDE_KM,
    MEAN_MOLECULAR_SPEED_MS,
    SPEED_OF_SOUND_MS,
    TEMPERATURE_K,
)

_ALTITUDE_KM = np.asarray(ALTITUDE_KM, dtype=np.float64)
_TEMPERATURE_K = np.asarray(TEMPERATURE_K, dtype=np.float64)
_SPEED_OF_SOUND_MS = np.asarray(SPEED_OF_SOUND_MS, dtype=np.float64)
_MEAN_MOLECULAR_SPEED_MS = np.asarray(
    MEAN_MOLECULAR_SPEED_MS,
    dtype=np.float64,
)

if not (
    _ALTITUDE_KM.shape
    == _TEMPERATURE_K.shape
    == _SPEED_OF_SOUND_MS.shape
    == _MEAN_MOLECULAR_SPEED_MS.shape
):
    raise RuntimeError("pinned US1976 columns must have equal lengths")
if not np.all(np.diff(_ALTITUDE_KM) > 0.0):
    raise RuntimeError("pinned US1976 altitudes must be strictly increasing")


def altitude_range_km() -> tuple[float, float]:
    """Return the pinned table's inclusive geometric-altitude range."""
    return float(_ALTITUDE_KM[0]), float(_ALTITUDE_KM[-1])


def sample_at_altitude_km(altitude_km: float) -> dict[str, float]:
    """Linearly interpolate the exact atmosphere columns used by legacy FMF."""
    altitude = float(altitude_km)
    if not math.isfinite(altitude):
        raise ValueError(f"Altitude_km must be finite, got {altitude!r}")
    minimum, maximum = altitude_range_km()
    if altitude < minimum or altitude > maximum:
        raise ValueError(
            f"Altitude_km={altitude} out of range [{minimum}, {maximum}]"
        )
    return {
        "T_K": float(np.interp(altitude, _ALTITUDE_KM, _TEMPERATURE_K)),
        "c_ms": float(np.interp(altitude, _ALTITUDE_KM, _SPEED_OF_SOUND_MS)),
        "Vmean_ms": float(
            np.interp(altitude, _ALTITUDE_KM, _MEAN_MOLECULAR_SPEED_MS)
        ),
    }


def mean_to_most_probable_speed(mean_speed_ms: float) -> float:
    """Convert mean molecular speed to the legacy most-probable speed."""
    return (math.sqrt(math.pi) / 2.0) * float(mean_speed_ms)


__all__ = (
    "altitude_range_km",
    "mean_to_most_probable_speed",
    "sample_at_altitude_km",
)
