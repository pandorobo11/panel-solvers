"""Application bootstrap for the shared Qt GUI."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import replace

from PySide6 import QtWidgets

from .main_window import MainWindow
from .solver_spec import SolverGuiAdapters, SolverSpec


class GuiAdaptersUnavailable(RuntimeError):
    """Raised when an explicitly unconfigured GUI specification is invoked."""


def _unavailable_adapters(product_id: str) -> SolverGuiAdapters:
    message = (
        f"{product_id} case I/O and execution adapters are not configured."
    )

    def unavailable(*_args, **_kwargs):
        raise GuiAdaptersUnavailable(message)

    return SolverGuiAdapters(
        read_cases=unavailable,
        build_case_signatures=unavailable,
        run_cases=unavailable,
        validate_output_path=unavailable,
        resolve_velocity_hat_stl=unavailable,
    )


def prepare_gui_spec(spec: SolverSpec) -> SolverSpec:
    """Supply explicit failing adapters only for an unconfigured specification."""
    if not isinstance(spec, SolverSpec):
        raise TypeError("spec must be a SolverSpec")
    if spec.adapters is not None:
        return spec
    return replace(spec, adapters=_unavailable_adapters(spec.product_id))


def create_main_window(
    spec: SolverSpec,
    *,
    window_factory: Callable[[SolverSpec], MainWindow] = MainWindow,
) -> MainWindow:
    """Construct the shared shell from one complete runtime specification."""
    if not callable(window_factory):
        raise TypeError("window_factory must be callable")
    adapters_were_missing = spec.adapters is None
    window = window_factory(prepare_gui_spec(spec))
    if adapters_were_missing:
        window.cases_panel.logln(
            "[ERROR] Case I/O and execution adapters are not configured."
        )
    return window


def run_gui(
    spec: SolverSpec,
    argv: Sequence[str] | None = None,
    *,
    application_factory: Callable[[list[str]], QtWidgets.QApplication] = (
        QtWidgets.QApplication
    ),
    window_factory: Callable[[SolverSpec], MainWindow] = MainWindow,
) -> int:
    """Show the shared window and run the Qt event loop."""
    application = QtWidgets.QApplication.instance()
    if application is None:
        if not callable(application_factory):
            raise TypeError("application_factory must be callable")
        application = application_factory(list(sys.argv if argv is None else argv))
    window = create_main_window(spec, window_factory=window_factory)
    window.show()
    return int(application.exec())


__all__ = (
    "GuiAdaptersUnavailable",
    "create_main_window",
    "prepare_gui_spec",
    "run_gui",
)
