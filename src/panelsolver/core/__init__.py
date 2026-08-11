"""Model-independent central contracts for the shared numerical pipeline."""

from .aggregation import aggregate_component_results, assemble_common_results
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
from .frames import (
    body_to_stability,
    stl_to_body,
    velocity_hat_stl_from_tangent_angles,
)
from .integration import PanelIntegration, integrate_panel_loads
from .mesh import MeshComponent, PanelMesh

__all__ = (
    "CommonCasePayload",
    "CommonResults",
    "ComponentResult",
    "ContractError",
    "ContractValueError",
    "IntegratedCoefficients",
    "LocalLoads",
    "MeshComponent",
    "ModelCasePayload",
    "NonFiniteError",
    "PanelFlowState",
    "PanelGeometry",
    "PanelIntegration",
    "PanelLoadModel",
    "PanelMesh",
    "PanelSolverError",
    "PayloadScalar",
    "PayloadValue",
    "ShapeError",
    "aggregate_component_results",
    "assemble_common_results",
    "body_to_stability",
    "integrate_panel_loads",
    "stl_to_body",
    "velocity_hat_stl_from_tangent_angles",
)
