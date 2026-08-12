"""FMF-only atmosphere compatibility package."""

from .us1976 import (
    altitude_range_km,
    load_us1976_tables,
    mean_to_most_probable_speed,
    sample_at_altitude_km,
)

__all__ = (
    "altitude_range_km",
    "load_us1976_tables",
    "mean_to_most_probable_speed",
    "sample_at_altitude_km",
)
