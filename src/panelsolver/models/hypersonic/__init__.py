"""Independent hypersonic pressure-model family."""

from .model import (
    HYPERSONIC_ALGORITHM_VERSION,
    HYPERSONIC_MODEL_ID,
    HypersonicCaseError,
    HypersonicModel,
    ResolvedHypersonicCase,
    resolve_hypersonic_case,
)
from .modified_newtonian import modified_newtonian_cp_max
from .prandtl_meyer import (
    _inverse_prandtl_meyer,
    _prandtl_meyer_nu,
    prandtl_meyer_pressure_coefficient,
)
from .selectors import (
    LEEWARD_EQUATION_VALUES,
    WINDWARD_EQUATION_VALUES,
    normalize_leeward_equation,
    normalize_windward_equation,
)
from .tangent_cone import (
    _tangent_cone_detach_limit,
    tangent_cone_pressure_coefficient,
)
from .tangent_wedge import (
    _tangent_wedge_detach_limit,
    tangent_wedge_pressure_coefficient,
)

__all__ = (
    "HYPERSONIC_ALGORITHM_VERSION",
    "HYPERSONIC_MODEL_ID",
    "LEEWARD_EQUATION_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "HypersonicCaseError",
    "HypersonicModel",
    "ResolvedHypersonicCase",
    "_inverse_prandtl_meyer",
    "_prandtl_meyer_nu",
    "_tangent_cone_detach_limit",
    "_tangent_wedge_detach_limit",
    "modified_newtonian_cp_max",
    "normalize_leeward_equation",
    "normalize_windward_equation",
    "prandtl_meyer_pressure_coefficient",
    "resolve_hypersonic_case",
    "tangent_cone_pressure_coefficient",
    "tangent_wedge_pressure_coefficient",
)
