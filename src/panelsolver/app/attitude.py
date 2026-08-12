"""Legacy attitude parsing with an explicit product domain policy."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

ATTITUDE_INPUT_VALUES = frozenset({"beta_tan", "beta_sin", "bank"})
_ZERO_DIRECTION_ATOL = 1.0e-14


@dataclass(frozen=True, slots=True, eq=False)
class ResolvedAttitude:
    """One public attitude input resolved to the tangent-angle convention."""

    velocity_hat_stl: np.ndarray
    alpha_t_deg: float
    beta_t_deg: float
    input_mode: str

    def __post_init__(self) -> None:
        velocity = np.asarray(self.velocity_hat_stl, dtype=np.float64)
        if velocity.shape != (3,) or not np.isfinite(velocity).all():
            raise ValueError("velocity_hat_stl must be a finite vector with shape (3,)")
        norm = float(np.linalg.norm(velocity))
        if norm < _ZERO_DIRECTION_ATOL:
            raise ValueError("velocity_hat_stl must have nonzero norm")
        immutable = np.frombuffer((velocity / norm).tobytes(), dtype=np.float64)
        object.__setattr__(self, "velocity_hat_stl", immutable)
        object.__setattr__(self, "alpha_t_deg", float(self.alpha_t_deg))
        object.__setattr__(self, "beta_t_deg", float(self.beta_t_deg))
        object.__setattr__(self, "input_mode", _attitude_mode(self.input_mode))


def _attitude_mode(value: object) -> str:
    mode = str(value or "").strip().lower() or "beta_tan"
    if mode not in ATTITUDE_INPUT_VALUES:
        raise ValueError(
            f"Invalid attitude_input: '{value}'. "
            "Expected one of: beta_tan, beta_sin, bank."
        )
    return mode


def _unit(values: tuple[float, float, float], *, message: str) -> np.ndarray:
    velocity = np.asarray(values, dtype=np.float64)
    norm = float(np.linalg.norm(velocity))
    if norm < _ZERO_DIRECTION_ATOL:
        raise ValueError(message)
    return velocity / norm


def resolve_attitude(
    alpha_deg: float,
    beta_or_bank_deg: float,
    attitude_input: object = None,
    *,
    strict_beta_tan_domain: bool,
) -> ResolvedAttitude:
    """Resolve a pinned public attitude while retaining the D007 policy split."""
    mode = _attitude_mode(attitude_input)
    alpha_in = float(alpha_deg)
    beta_in = float(beta_or_bank_deg)
    if not math.isfinite(alpha_in) or not math.isfinite(beta_in):
        raise ValueError("attitude angles must be finite")

    if mode == "beta_tan":
        if strict_beta_tan_domain and (
            not -90.0 < alpha_in < 90.0 or not -90.0 < beta_in < 90.0
        ):
            raise ValueError(
                "attitude_input='beta_tan' requires alpha_deg and "
                "beta_or_bank_deg to be strictly between -90 and 90 degrees."
            )
        alpha_rad = math.radians(alpha_in)
        beta_rad = math.radians(beta_in)
        cos_alpha = math.cos(alpha_rad)
        velocity = _unit(
            (
                cos_alpha * math.cos(beta_rad),
                -math.sin(beta_rad) * cos_alpha,
                math.sin(alpha_rad) * math.cos(beta_rad),
            ),
            message="Invalid alpha/beta leading to zero direction.",
        )
        return ResolvedAttitude(velocity, alpha_in, beta_in, mode)

    if mode == "bank":
        alpha_rad = math.radians(alpha_in)
        bank_rad = math.radians(beta_in)
        velocity = _unit(
            (
                math.cos(alpha_rad),
                -math.sin(alpha_rad) * math.sin(bank_rad),
                math.sin(alpha_rad) * math.cos(bank_rad),
            ),
            message="Invalid bank-angle inputs leading to zero direction.",
        )
    else:
        alpha_rad = math.radians(alpha_in)
        beta_sin_rad = math.radians(beta_in)
        tangent_alpha = math.tan(alpha_rad)
        sin_beta = math.sin(beta_sin_rad)
        x_squared = (1.0 - sin_beta * sin_beta) / (
            1.0 + tangent_alpha * tangent_alpha
        )
        if x_squared < -1.0e-14:
            raise ValueError("Inconsistent alpha_t/beta_s inputs.")
        x_squared = max(x_squared, 0.0)
        x_value = (1.0 if math.cos(alpha_rad) >= 0.0 else -1.0) * math.sqrt(
            x_squared
        )
        velocity = _unit(
            (x_value, -sin_beta, tangent_alpha * x_value),
            message="Invalid beta-sin inputs leading to zero direction.",
        )

    alpha_t_deg = math.degrees(math.atan2(float(velocity[2]), float(velocity[0])))
    beta_t_deg = math.degrees(math.atan2(float(-velocity[1]), float(velocity[0])))
    return ResolvedAttitude(velocity, alpha_t_deg, beta_t_deg, mode)


__all__ = (
    "ATTITUDE_INPUT_VALUES",
    "ResolvedAttitude",
    "resolve_attitude",
)
