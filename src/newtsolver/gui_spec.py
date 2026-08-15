"""Legacy newtsolver GUI identity over canonical Hypersonic composition."""

from __future__ import annotations

from dataclasses import replace

from panelsolver.app import SolverGuiAdapters, SolverSpec
from panelsolver.domains.hypersonic import format_case
from panelsolver.domains.hypersonic import gui_spec as canonical_gui_spec

_DEFAULT_ADAPTERS = object()


def solver_spec(
    *,
    adapters: SolverGuiAdapters | None | object = _DEFAULT_ADAPTERS,
) -> SolverSpec:
    """Return canonical Hypersonic behavior with the legacy visible identity."""
    if adapters is _DEFAULT_ADAPTERS:
        from .runtime import GUI_ADAPTERS

        selected_adapters = GUI_ADAPTERS
    else:
        selected_adapters = adapters
    return replace(
        canonical_gui_spec(adapters=selected_adapters),
        product_id="newtsolver",
        window_title="newtsolver (GUI)",
    )


__all__ = ("format_case", "solver_spec")
