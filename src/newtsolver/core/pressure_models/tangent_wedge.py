# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""Tangent-wedge compatibility callables."""

from functools import lru_cache

from panelsolver.models.hypersonic.tangent_wedge import (
    _oblique_theta_from_beta as _shared_oblique_theta_from_beta,
)
from panelsolver.models.hypersonic.tangent_wedge import (
    _tangent_wedge_detach_limit as _shared_tangent_wedge_detach_limit,
)
from panelsolver.models.hypersonic.tangent_wedge import (
    _weak_oblique_shock_beta as _shared_weak_oblique_shock_beta,
)
from panelsolver.models.hypersonic.tangent_wedge import (
    tangent_wedge_pressure_coefficient as _shared_pressure_coefficient,
)


def _oblique_theta_from_beta(
    Mach: "float",
    gamma: "float",
    beta: "float",
) -> "float":
    """Delegate the frozen helper to the shared pressure implementation."""
    return _shared_oblique_theta_from_beta(Mach, gamma, beta)


@lru_cache(maxsize=256)
def _tangent_wedge_detach_limit(
    Mach: "float",
    gamma: "float",
) -> "tuple[float, float]":
    """Retain the pinned public cache while delegating the calculation."""
    return _shared_tangent_wedge_detach_limit.__wrapped__(Mach, gamma)


def _weak_oblique_shock_beta(
    Mach: "float",
    gamma: "float",
    theta: "np.ndarray",
) -> "np.ndarray":
    """Delegate the frozen helper to the shared pressure implementation."""
    return _shared_weak_oblique_shock_beta(Mach, gamma, theta)


def tangent_wedge_pressure_coefficient(
    Mach: "float",
    gamma: "float",
    deltar: "float | np.ndarray",
    *,
    cp_cap: "float | None" = None,
) -> "np.ndarray":
    """Delegate the frozen public call to the shared pressure equation."""
    return _shared_pressure_coefficient(Mach, gamma, deltar, cp_cap=cp_cap)

__all__ = (
    "_oblique_theta_from_beta",
    "_tangent_wedge_detach_limit",
    "_weak_oblique_shock_beta",
    "tangent_wedge_pressure_coefficient",
)
