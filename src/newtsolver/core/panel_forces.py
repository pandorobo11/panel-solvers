"""newtsolver panel-force call forwarded to the shared model."""

from panelsolver.models.hypersonic.model import panel_force_density
from panelsolver.models.hypersonic.selectors import (
    LEEWARD_EQUATION_VALUES,
    WINDWARD_EQUATION_VALUES,
)

__all__ = (
    "LEEWARD_EQUATION_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "panel_force_density",
)
