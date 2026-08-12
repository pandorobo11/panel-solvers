# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""FMF-specific model helpers forwarded to accepted shared implementations."""

from panelsolver.app.attitude import resolve_attitude
from panelsolver.core.frames import rotation_matrix_y_rad
from panelsolver.core.frames import stl_to_body as _shared_stl_to_body
from panelsolver.models.sentman import (
    sentman_dC_dA_vector as _shared_sentman_dC_dA_vector,
)
from panelsolver.models.sentman import (
    sentman_dC_dA_vectors as _shared_sentman_dC_dA_vectors,
)

ATTITUDE_INPUT_VALUES = {"beta_tan", "beta_sin", "bank"}


def sentman_dC_dA_vector(
    Vhat: "np.ndarray",
    n_out: "np.ndarray",
    S: "float",
    Ti: "float",
    Tw: "float",
    Aref: "float",
    shielded: "bool" = False,
) -> "np.ndarray":
    """Delegate the pinned FMF callable shape to the shared equation."""
    return _shared_sentman_dC_dA_vector(Vhat, n_out, S, Ti, Tw, Aref, shielded)


def sentman_dC_dA_vectors(
    Vhat: "np.ndarray",
    n_out: "np.ndarray",
    S: "float",
    Ti: "float",
    Tw: "float",
    Aref: "float",
    shielded: "np.ndarray | bool" = False,
) -> "np.ndarray":
    """Delegate the pinned vectorized FMF callable to the shared equation."""
    return _shared_sentman_dC_dA_vectors(Vhat, n_out, S, Ti, Tw, Aref, shielded)


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
        strict_beta_tan_domain=True,
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
    "resolve_attitude_to_vhat",
    "rot_y",
    "sentman_dC_dA_vector",
    "sentman_dC_dA_vectors",
    "stl_to_body",
)
