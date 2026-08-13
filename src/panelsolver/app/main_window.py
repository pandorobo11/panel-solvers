"""Shared GUI shell with a common cooperative close lifecycle."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from .cases_panel import CasesPanel
from .solver_spec import SolverSpec
from .viewer import ViewerPanel


class MainWindow(QtWidgets.QMainWindow):
    """Wire shared cases and viewer panels with common lifecycle behavior."""

    def __init__(
        self,
        spec: SolverSpec,
        *,
        cases_panel: QtWidgets.QWidget | None = None,
        viewer_panel: QtWidgets.QWidget | None = None,
    ) -> None:
        if not isinstance(spec, SolverSpec):
            raise TypeError("spec must be a SolverSpec")
        super().__init__()
        self.spec = spec
        self.setWindowTitle(spec.window_title)
        self.resize(1480, 900)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        self.cases_panel = cases_panel or CasesPanel(spec)
        self.viewer_panel = viewer_panel or ViewerPanel(spec)
        self.splitter.addWidget(self.cases_panel)
        self.splitter.addWidget(self.viewer_panel)
        self.splitter.setStretchFactor(1, 4)
        self._close_when_run_finishes = False

        self.viewer_panel.log_message.connect(self.cases_panel.logln)
        self.cases_panel.vtp_loaded.connect(self.viewer_panel.load_vtp)
        self.cases_panel.viewer_clear_requested.connect(self.viewer_panel.clear_view)
        self.cases_panel.cases_updated.connect(self.viewer_panel.set_case_rows)
        self.cases_panel.run_finished.connect(self._on_case_run_finished)
        self.viewer_panel.save_selected_images_requested.connect(
            self._on_save_selected_images
        )

    @QtCore.Slot()
    def _on_save_selected_images(self) -> None:
        rows = self.cases_panel.selected_case_rows()
        if not rows:
            self.cases_panel.logln(
                "[WARN] Select at least one case to batch-save images."
            )
            return
        self.viewer_panel.save_images_for_case_rows(rows)

    def closeEvent(self, event) -> None:
        """Cancel an active run and defer close until its thread is cleaned up."""
        if self.cases_panel.is_running():
            if not self._close_when_run_finishes:
                self._close_when_run_finishes = True
                self.cases_panel.cancel_run()
                self.cases_panel.logln(
                    "[CLOSE] Waiting for the active run to stop..."
                )
            event.ignore()
            return
        super().closeEvent(event)

    @QtCore.Slot()
    def _on_case_run_finished(self) -> None:
        if self._close_when_run_finishes:
            self._close_when_run_finishes = False
            QtCore.QTimer.singleShot(0, self.close)


__all__ = ("MainWindow",)
