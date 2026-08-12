"""Shared command-line and graphical application layer."""

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
    "AdaptedLegacyPanels",
    "ArtifactCaseMatch",
    "ArtifactLoadMode",
    "ArtifactSignatureCandidates",
    "AtomicCsvWritePolicy",
    "ClosePolicy",
    "LegacyPanelSnapshot",
    "LegacyPhase3Projection",
    "LegacyRunContext",
    "ScalarField",
    "SolverGuiAdapters",
    "SolverSpec",
    "TempNameStyle",
    "adapt_legacy_panels",
    "artifact_display_allowed",
    "default_model_registry",
    "discover_scalar_fields",
    "field_data_scalar",
    "match_artifact_case",
    "project_legacy_phase3_case",
    "request_from_registry",
    "resolve_matching_case_row",
    "scalar_color_limits",
    "validate_csv_output_path",
    "write_csv_atomic",
)
