"""Model-independent central contracts for the shared numerical pipeline."""

from .contracts import (
    CommonCasePayload,
    CommonResults,
    ComponentResult,
    IntegratedCoefficients,
    LocalLoads,
    ModelCasePayload,
    PanelFlowState,
    PanelGeometry,
    PanelLoadModel,
    PayloadScalar,
    PayloadValue,
)
from .errors import (
    ContractError,
    ContractValueError,
    NonFiniteError,
    PanelSolverError,
    ShapeError,
)

__all__ = (
    "CommonCasePayload",
    "CommonResults",
    "ComponentResult",
    "ContractError",
    "ContractValueError",
    "IntegratedCoefficients",
    "LocalLoads",
    "ModelCasePayload",
    "NonFiniteError",
    "PanelFlowState",
    "PanelGeometry",
    "PanelLoadModel",
    "PanelSolverError",
    "PayloadScalar",
    "PayloadValue",
    "ShapeError",
)
