"""Model-independent central contracts for the shared numerical pipeline."""

from .aggregation import aggregate_component_results, assemble_common_results
from .artifacts import (
    ArtifactProjectionPolicy,
    NpzProjection,
    VtpProjection,
    project_npz_artifact,
    project_vtp_artifact,
)
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
from .csv_projection import (
    CsvCell,
    CsvProjection,
    CsvProjectionPolicy,
    project_summary_csv,
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
    "ArtifactProjectionPolicy",
    "CommonCasePayload",
    "CommonResults",
    "ComponentResult",
    "ContractError",
    "ContractValueError",
    "CsvCell",
    "CsvProjection",
    "CsvProjectionPolicy",
    "IntegratedCoefficients",
    "LocalLoads",
    "MeshComponent",
    "ModelCasePayload",
    "NonFiniteError",
    "NpzProjection",
    "PanelFlowState",
    "PanelGeometry",
    "PanelIntegration",
    "PanelLoadModel",
    "PanelMesh",
    "PanelSolverError",
    "PayloadScalar",
    "PayloadValue",
    "ShapeError",
    "VtpProjection",
    "aggregate_component_results",
    "assemble_common_results",
    "body_to_stability",
    "integrate_panel_loads",
    "project_npz_artifact",
    "project_summary_csv",
    "project_vtp_artifact",
    "stl_to_body",
    "velocity_hat_stl_from_tangent_angles",
)
