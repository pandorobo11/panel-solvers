"""Qt worker boundary for product-adapted case execution."""

from __future__ import annotations

import threading
from collections.abc import Sequence
from pathlib import Path

from PySide6 import QtCore

from panelsolver.core import SchedulerCancelled

from .solver_spec import CaseRow, GuiRunRequest, GuiRunResult, RunCasesCallback


class CaseRunWorker(QtCore.QObject):
    """Run one adapter callback and expose only queued Qt signals to widgets."""

    log = QtCore.Signal(str)
    progress = QtCore.Signal(int, int)
    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    canceled = QtCore.Signal()

    def __init__(
        self,
        run_cases: RunCasesCallback,
        rows: Sequence[CaseRow],
        workers: int,
        checkpoint_every_cases: int,
        output_path: str | Path,
    ) -> None:
        super().__init__()
        if not callable(run_cases):
            raise TypeError("run_cases must be callable")
        self._run_cases = run_cases
        self._rows = tuple(rows)
        self._workers = workers
        self._checkpoint_every_cases = checkpoint_every_cases
        self._output_path = Path(output_path)
        self._cancel_event = threading.Event()

    @QtCore.Slot()
    def run(self) -> None:
        """Execute until completion, primary failure, or boundary cancellation."""
        try:
            request = GuiRunRequest(
                rows=self._rows,
                workers=self._workers,
                checkpoint_every_cases=self._checkpoint_every_cases,
                output_path=self._output_path,
                log=self.log.emit,
                progress=self.progress.emit,
                cancel_requested=self._cancel_event.is_set,
            )
            result = self._run_cases(request)
            if not isinstance(result, GuiRunResult):
                raise TypeError("run_cases must return a GuiRunResult")
        except SchedulerCancelled:
            self.canceled.emit()
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        if self._cancel_event.is_set():
            self.canceled.emit()
            return
        self.completed.emit(result)

    def cancel(self) -> None:
        """Request cancellation; the adapter observes it at case boundaries."""
        self._cancel_event.set()


__all__ = ("CaseRunWorker",)
