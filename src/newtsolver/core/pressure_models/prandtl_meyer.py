# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""Prandtl-Meyer compatibility callables."""

from panelsolver.models.hypersonic.prandtl_meyer import (
    _inverse_prandtl_meyer as _shared_inverse_prandtl_meyer,
)
from panelsolver.models.hypersonic.prandtl_meyer import (
    _prandtl_meyer_nu as _shared_prandtl_meyer_nu,
)
from panelsolver.models.hypersonic.prandtl_meyer import (
    prandtl_meyer_pressure_coefficient as _shared_pressure_coefficient,
)


def _prandtl_meyer_nu(
    Mach: "np.ndarray",
    gamma: "float",
) -> "np.ndarray":
    """Delegate the frozen helper to the shared pressure implementation."""
    return _shared_prandtl_meyer_nu(Mach, gamma)


def _inverse_prandtl_meyer(
    nu_target: "np.ndarray",
    gamma: "float",
) -> "np.ndarray":
    """Delegate the frozen inverse helper to the shared implementation."""
    return _shared_inverse_prandtl_meyer(nu_target, gamma)


def prandtl_meyer_pressure_coefficient(
    Mach: "float",
    gamma: "float",
    deltar: "float | np.ndarray",
) -> "np.ndarray":
    """Delegate the frozen public call to the shared pressure equation."""
    return _shared_pressure_coefficient(Mach, gamma, deltar)

__all__ = (
    "_inverse_prandtl_meyer",
    "_prandtl_meyer_nu",
    "prandtl_meyer_pressure_coefficient",
)
