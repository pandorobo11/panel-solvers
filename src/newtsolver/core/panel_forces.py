# ruff: noqa: F821 - freeze NumPy annotation text without importing it here
"""newtsolver panel-force call forwarded to the shared model."""

from panelsolver.models.hypersonic.model import (
    panel_force_density as _shared_panel_force_density,
)
from panelsolver.models.hypersonic.selectors import (
    LEEWARD_EQUATION_VALUES,
    WINDWARD_EQUATION_VALUES,
)


def panel_force_density(
    Vhat: "np.ndarray",
    n_out: "np.ndarray",
    Aref: "float",
    shielded: "np.ndarray | bool" = False,
    face_stl_index: "np.ndarray | None" = None,
    cp_max: "float" = 2.0,
    windward_eq: "str" = "newtonian",
    leeward_eq: "str" = "shield",
    windward_eq_by_component: "list[str] | tuple[str, ...] | None" = None,
    leeward_eq_by_component: "list[str] | tuple[str, ...] | None" = None,
    Mach: "float | None" = None,
    gamma: "float | None" = None,
) -> "np.ndarray":
    """Delegate the frozen newtsolver call shape to the shared model."""
    return _shared_panel_force_density(
        Vhat,
        n_out,
        Aref,
        shielded,
        face_stl_index,
        cp_max,
        windward_eq,
        leeward_eq,
        windward_eq_by_component,
        leeward_eq_by_component,
        Mach,
        gamma,
    )

__all__ = (
    "LEEWARD_EQUATION_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "panel_force_density",
)
