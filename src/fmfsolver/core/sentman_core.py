"""FMF-specific model helpers forwarded to accepted shared implementations."""

from panelsolver.app.attitude import resolve_attitude
from panelsolver.core.frames import rotation_matrix_y_rad, stl_to_body
from panelsolver.models.sentman import sentman_dC_dA_vector, sentman_dC_dA_vectors

ATTITUDE_INPUT_VALUES = {"beta_tan", "beta_sin", "bank"}


def resolve_attitude_to_vhat(
    alpha_deg: float,
    beta_deg: float,
    attitude_input: str | None = None,
):
    resolved = resolve_attitude(
        alpha_deg,
        beta_deg,
        attitude_input,
    )
    return (
        resolved.velocity_hat_stl,
        resolved.alpha_t_deg,
        resolved.beta_t_deg,
        resolved.input_mode,
    )


def rot_y(alpha_rad: float):
    return rotation_matrix_y_rad(alpha_rad)


__all__ = (
    "ATTITUDE_INPUT_VALUES",
    "resolve_attitude_to_vhat",
    "rot_y",
    "sentman_dC_dA_vector",
    "sentman_dC_dA_vectors",
    "stl_to_body",
)
