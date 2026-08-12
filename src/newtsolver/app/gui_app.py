"""newtsolver selector for the shared graphical application."""

from __future__ import annotations

from typing import NoReturn

from panelsolver.app import gui_bootstrap

from ..gui_spec import solver_spec


def main() -> NoReturn:
    """Launch the shared GUI with the pinned newtsolver specification."""
    raise SystemExit(gui_bootstrap.run_gui(solver_spec()))


__all__ = ("main",)
