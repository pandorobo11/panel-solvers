"""newtsolver attitude policy over shared transforms."""

from panelsolver.app import attitude as _shared_attitude
from panelsolver.app.attitude import resolve_attitude
from panelsolver.app.attitude import resolve_attitude_mode as _resolve_attitude_mode
from panelsolver.core.frames import rotation_matrix_y_rad, stl_to_body

ATTITUDE_INPUT_VALUES = set(_shared_attitude.ATTITUDE_INPUT_VALUES)


def resolve_attitude_to_vhat(
    alpha_deg: float,
    beta_deg: float,
    attitude_input: str | None = None,
):
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


def rot_y(alpha_rad: float):
    return rotation_matrix_y_rad(alpha_rad)


__all__ = (
    "ATTITUDE_INPUT_VALUES",
    "_resolve_attitude_mode",
    "resolve_attitude_to_vhat",
    "rot_y",
    "stl_to_body",
)
