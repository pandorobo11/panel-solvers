"""No-spec FMF cases panel over the shared widget."""

from panelsolver.app.cases_panel import (
    CasesPanel as _SharedCasesPanel,
)
from panelsolver.app.cases_panel import (
    ValidationIssuesDialog as _ValidationIssuesDialog,  # noqa: F401
)
from panelsolver.app.run_lifecycle import CaseRunWorker as _CaseRunWorker  # noqa: F401

from ..gui_spec import solver_spec


class CasesPanel(_SharedCasesPanel):
    def __init__(self, parent=None):
        super().__init__(solver_spec(), parent)


__all__ = ("CasesPanel",)
