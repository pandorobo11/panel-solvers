"""No-argument newtsolver window over the shared GUI shell."""

from panelsolver.app.main_window import MainWindow as _SharedMainWindow

from ..gui_spec import solver_spec


class MainWindow(_SharedMainWindow):
    def __init__(self):
        super().__init__(solver_spec())


__all__ = ("MainWindow",)
