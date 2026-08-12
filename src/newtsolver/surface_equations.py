"""Frozen selector helpers forwarded to the shared hypersonic model."""

from panelsolver.models.hypersonic.selectors import (
    LEEWARD_EQUATION_VALUES,
    WINDWARD_EQUATION_VALUES,
)
from panelsolver.models.hypersonic.selectors import (
    count_semicolon_entries as _shared_count_semicolon_entries,
)
from panelsolver.models.hypersonic.selectors import (
    expand_equations_for_components as _shared_expand_equations_for_components,
)
from panelsolver.models.hypersonic.selectors import (
    normalize_leeward_equation as _shared_normalize_leeward_equation,
)
from panelsolver.models.hypersonic.selectors import (
    normalize_windward_equation as _shared_normalize_windward_equation,
)
from panelsolver.models.hypersonic.selectors import (
    split_semicolon_tokens as _shared_split_semicolon_tokens,
)


def normalize_windward_equation(value: "str | None") -> "str":
    """Delegate selector normalization through the frozen module identity."""
    return _shared_normalize_windward_equation(value)


def normalize_leeward_equation(value: "str | None") -> "str":
    """Delegate selector normalization through the frozen module identity."""
    return _shared_normalize_leeward_equation(value)


def split_semicolon_tokens(value: "str | None") -> "list[str]":
    """Delegate selector splitting through the frozen module identity."""
    return _shared_split_semicolon_tokens(value)


def count_semicolon_entries(value: "str | None") -> "int":
    """Delegate selector counting through the frozen module identity."""
    return _shared_count_semicolon_entries(value)


def expand_equations_for_components(
    raw_value: "str | None",
    *,
    default_value: "str",
    resolver,
    n_components: "int",
    field_name: "str",
) -> "tuple[list[str], str]":
    """Delegate frozen component expansion without owning selector logic."""
    return _shared_expand_equations_for_components(
        raw_value,
        default_value=default_value,
        resolver=resolver,
        n_components=n_components,
        field_name=field_name,
    )

__all__ = (
    "LEEWARD_EQUATION_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "count_semicolon_entries",
    "expand_equations_for_components",
    "normalize_leeward_equation",
    "normalize_windward_equation",
    "split_semicolon_tokens",
)
