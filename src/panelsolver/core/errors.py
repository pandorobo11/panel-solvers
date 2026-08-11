"""Stable exception taxonomy for shared panel-solver contracts."""

from __future__ import annotations

from collections.abc import Sequence


class PanelSolverError(Exception):
    """Base class for errors raised by the shared platform."""


class ContractError(PanelSolverError, ValueError):
    """Base class for invalid central-contract data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.detail = message
        super().__init__(f"{field}: {message}")


class ShapeError(ContractError):
    """An array does not have the shape required by its contract field."""

    def __init__(
        self,
        field: str,
        *,
        expected: Sequence[int | str],
        actual: Sequence[int],
    ) -> None:
        self.expected = tuple(expected)
        self.actual = tuple(actual)
        super().__init__(field, f"expected shape {self.expected}, got {self.actual}")


class NonFiniteError(ContractError):
    """A numerical contract field contains NaN or infinity."""

    def __init__(self, field: str) -> None:
        super().__init__(field, "must contain only finite values")


class ContractValueError(ContractError):
    """A finite, correctly shaped field still violates its value contract."""


__all__ = (
    "ContractError",
    "ContractValueError",
    "NonFiniteError",
    "PanelSolverError",
    "ShapeError",
)
