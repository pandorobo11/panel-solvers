# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""Tangent-cone compatibility callables."""

from functools import lru_cache

from panelsolver.models.hypersonic.tangent_cone import (
    _tangent_cone_detach_limit as _shared_tangent_cone_detach_limit,
)
from panelsolver.models.hypersonic.tangent_cone import (
    tangent_cone_pressure_coefficient as _shared_pressure_coefficient,
)


@lru_cache(maxsize=128)
def _tangent_cone_detach_limit(
    Mach: "float",
    gamma: "float",
) -> "tuple[float, float]":
    """Retain the pinned public cache while delegating the calculation."""
    return _shared_tangent_cone_detach_limit.__wrapped__(Mach, gamma)


def tangent_cone_pressure_coefficient(
    Mach: "float",
    gamma: "float",
    deltar: "float | np.ndarray",
    *,
    cp_cap: "float | None" = None,
) -> "np.ndarray":
    """Delegate the frozen public call to the shared pressure equation."""
    return _shared_pressure_coefficient(Mach, gamma, deltar, cp_cap=cp_cap)

__all__ = ("_tangent_cone_detach_limit", "tangent_cone_pressure_coefficient")
