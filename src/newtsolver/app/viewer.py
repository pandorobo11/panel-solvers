"""No-spec newtsolver viewer over the shared widget."""

from panelsolver.app.viewer import ViewerPanel as _SharedViewerPanel

from ..gui_spec import solver_spec


class ViewerPanel(_SharedViewerPanel):
    def __init__(self, parent=None):
        super().__init__(solver_spec(), parent)


__all__ = ("ViewerPanel",)
