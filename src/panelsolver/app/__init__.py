"""Shared command-line and graphical application layer."""

from .attitude import ATTITUDE_INPUT_VALUES, ResolvedAttitude, resolve_attitude
from .case_adapter import (
    AdaptedCase,
    ProductCasePolicy,
    adapt_case_row,
    build_artifact_signature_candidates,
)
from .case_io import (
    CaseReaderPolicy,
    InputValidationError,
    ValidationIssue,
    read_case_table,
)
from .csv_writer import (
    AtomicCsvWritePolicy,
    TempNameStyle,
    validate_csv_output_path,
    write_csv_atomic,
)
from .execution import default_model_registry, request_from_registry
from .legacy_adapter import (
    AdaptedLegacyPanels,
    LegacyPanelSnapshot,
    LegacyPhase3Projection,
    LegacyRunContext,
    adapt_legacy_panels,
    project_legacy_phase3_case,
)
from .solver_spec import (
    ArtifactSignatureCandidates,
    ClosePolicy,
    GuiRunRequest,
    GuiRunResult,
    SolverGuiAdapters,
    SolverSpec,
)
from .viewer_data import (
    ArtifactCaseMatch,
    ArtifactLoadMode,
    ScalarField,
    artifact_display_allowed,
    discover_scalar_fields,
    field_data_scalar,
    match_artifact_case,
    resolve_matching_case_row,
    scalar_color_limits,
)

__all__ = (
    "ATTITUDE_INPUT_VALUES",
    "AdaptedCase",
    "AdaptedLegacyPanels",
    "ArtifactCaseMatch",
    "ArtifactLoadMode",
    "ArtifactSignatureCandidates",
    "AtomicCsvWritePolicy",
    "CaseReaderPolicy",
    "ClosePolicy",
    "GuiRunRequest",
    "GuiRunResult",
    "InputValidationError",
    "LegacyPanelSnapshot",
    "LegacyPhase3Projection",
    "LegacyRunContext",
    "ProductCasePolicy",
    "ResolvedAttitude",
    "ScalarField",
    "SolverGuiAdapters",
    "SolverSpec",
    "TempNameStyle",
    "ValidationIssue",
    "adapt_case_row",
    "adapt_legacy_panels",
    "artifact_display_allowed",
    "build_artifact_signature_candidates",
    "default_model_registry",
    "discover_scalar_fields",
    "field_data_scalar",
    "match_artifact_case",
    "project_legacy_phase3_case",
    "read_case_table",
    "request_from_registry",
    "resolve_attitude",
    "resolve_matching_case_row",
    "scalar_color_limits",
    "validate_csv_output_path",
    "write_csv_atomic",
)
