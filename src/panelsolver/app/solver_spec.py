"""Model-neutral configuration for the shared graphical application."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

type CaseRow = Mapping[str, object]
type ReadCasesCallback = Callable[[str | Path], Sequence[CaseRow]]
type BuildCaseSignaturesCallback = Callable[[CaseRow], object]
type RunCasesCallback = Callable[[object], object]
type ValidateOutputPathCallback = Callable[
    [str | Path, str | Path, Sequence[CaseRow]], Path
]
type ResolveVelocityCallback = Callable[[CaseRow], object]
type FormatCaseCallback = Callable[[CaseRow], str]


class ClosePolicy(str, Enum):
    """Product-selected behavior when a window closes during an active run."""

    DEFER_UNTIL_IDLE = "defer_until_idle"
    IMMEDIATE = "immediate"


@dataclass(frozen=True, slots=True)
class SolverGuiAdapters:
    """Phase-owned adapters injected at the shared GUI boundary.

    Phase 6 defines the complete injection point so widgets never import a
    compatibility frontend. Product-compatible implementations of case reading,
    execution, and output validation remain Phase 7 work.
    """

    read_cases: ReadCasesCallback
    build_case_signatures: BuildCaseSignaturesCallback
    run_cases: RunCasesCallback
    validate_output_path: ValidateOutputPathCallback
    resolve_velocity_hat_stl: ResolveVelocityCallback

    def __post_init__(self) -> None:
        for field_name in (
            "read_cases",
            "build_case_signatures",
            "run_cases",
            "validate_output_path",
            "resolve_velocity_hat_stl",
        ):
            if not callable(getattr(self, field_name)):
                raise TypeError(f"SolverGuiAdapters.{field_name} must be callable")


def _nonempty_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _unique_names(value: object, *, field: str) -> tuple[str, ...]:
    if isinstance(value, str):
        raise TypeError(f"{field} must be an iterable of names, not a string")
    try:
        iterator = iter(value)
    except TypeError as exc:
        raise TypeError(f"{field} must be an iterable of names") from exc
    names = tuple(
        _nonempty_text(item, field=f"{field} item")
        for item in iterator
    )
    if not names:
        raise ValueError(f"{field} must not be empty")
    if len(names) != len(set(names)):
        raise ValueError(f"{field} must contain unique names")
    return names


@dataclass(frozen=True, slots=True)
class SolverSpec:
    """Identity and presentation policy consumed by every shared GUI widget."""

    product_id: str
    model_id: str
    window_title: str
    case_columns: tuple[str, ...]
    preferred_scalars: tuple[str, ...]
    format_case: FormatCaseCallback
    close_policy: ClosePolicy
    adapters: SolverGuiAdapters | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "product_id",
            _nonempty_text(self.product_id, field="SolverSpec.product_id"),
        )
        object.__setattr__(
            self,
            "model_id",
            _nonempty_text(self.model_id, field="SolverSpec.model_id"),
        )
        object.__setattr__(
            self,
            "window_title",
            _nonempty_text(self.window_title, field="SolverSpec.window_title"),
        )
        object.__setattr__(
            self,
            "case_columns",
            _unique_names(self.case_columns, field="SolverSpec.case_columns"),
        )
        if self.case_columns[0] != "case_id":
            raise ValueError("SolverSpec.case_columns must start with 'case_id'")
        object.__setattr__(
            self,
            "preferred_scalars",
            _unique_names(
                self.preferred_scalars,
                field="SolverSpec.preferred_scalars",
            ),
        )
        if not callable(self.format_case):
            raise TypeError("SolverSpec.format_case must be callable")
        if not isinstance(self.close_policy, ClosePolicy):
            raise TypeError("SolverSpec.close_policy must be a ClosePolicy")
        if self.adapters is not None and not isinstance(
            self.adapters,
            SolverGuiAdapters,
        ):
            raise TypeError("SolverSpec.adapters must be SolverGuiAdapters or None")


__all__ = (
    "BuildCaseSignaturesCallback",
    "CaseRow",
    "ClosePolicy",
    "FormatCaseCallback",
    "ReadCasesCallback",
    "ResolveVelocityCallback",
    "RunCasesCallback",
    "SolverGuiAdapters",
    "SolverSpec",
    "ValidateOutputPathCallback",
)
