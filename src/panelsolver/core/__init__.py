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
from .mesh_loading import (
    GEOMETRY_FINGERPRINT_SCHEMA_VERSION,
    MESH_LOADER_ALGORITHM_VERSION,
    LoadedPanelMesh,
    MeshCacheStats,
    MeshLoadError,
    MeshSourceFingerprint,
    MeshValidationPolicy,
    clear_mesh_cache,
    geometry_fingerprint,
    load_panel_mesh,
    mesh_cache_stats,
)

__all__ = (
    "GEOMETRY_FINGERPRINT_SCHEMA_VERSION",
    "MESH_LOADER_ALGORITHM_VERSION",
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
    "LoadedPanelMesh",
    "LocalLoads",
    "MeshCacheStats",
    "MeshComponent",
    "MeshLoadError",
    "MeshSourceFingerprint",
    "MeshValidationPolicy",
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
    "clear_mesh_cache",
    "geometry_fingerprint",
    "integrate_panel_loads",
    "load_panel_mesh",
    "mesh_cache_stats",
    "project_npz_artifact",
    "project_summary_csv",
    "project_vtp_artifact",
    "stl_to_body",
    "velocity_hat_stl_from_tangent_angles",
)
