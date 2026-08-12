# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""newtsolver attitude policy over shared transforms."""

from panelsolver.app import attitude as _shared_attitude
from panelsolver.app.attitude import resolve_attitude
from panelsolver.app.attitude import (
    resolve_attitude_mode as _shared_resolve_attitude_mode,
)
from panelsolver.core.frames import rotation_matrix_y_rad
from panelsolver.core.frames import stl_to_body as _shared_stl_to_body

ATTITUDE_INPUT_VALUES = set(_shared_attitude.ATTITUDE_INPUT_VALUES)


def _resolve_attitude_mode(attitude_input: "str | None") -> "str":
    """Delegate the pinned keyword through the newtsolver function identity."""
    return _shared_resolve_attitude_mode(attitude_input)


def stl_to_body(v_stl: "np.ndarray") -> "np.ndarray":
    """Delegate the pinned ``v_stl`` keyword to the shared frame transform."""
    return _shared_stl_to_body(v_stl)


def resolve_attitude_to_vhat(
    alpha_deg: "float",
    beta_deg: "float",
    attitude_input: "str | None" = None,
) -> "tuple[np.ndarray, float, float, str]":
    resolved = resolve_attitude(
        alpha_deg,
        beta_deg,
        attitude_input,
        strict_beta_tan_domain=False,
    )
    return (
        resolved.velocity_hat_stl,
        resolved.alpha_t_deg,
        resolved.beta_t_deg,
        resolved.input_mode,
    )


def rot_y(alpha_rad: "float") -> "np.ndarray":
    return rotation_matrix_y_rad(alpha_rad)


__all__ = (
    "ATTITUDE_INPUT_VALUES",
    "_resolve_attitude_mode",
    "resolve_attitude_to_vhat",
    "rot_y",
    "stl_to_body",
)
