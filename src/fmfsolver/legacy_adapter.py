"""FMF policy wrapper for the Phase 3 computed-data adapter."""

from __future__ import annotations

from collections.abc import Mapping

from panelsolver.app.legacy_adapter import (
    LegacyPanelSnapshot,
    LegacyPhase3Projection,
    LegacyRunContext,
    project_legacy_phase3_case,
)
from panelsolver.core import (
    ArtifactProjectionPolicy,
    CommonCasePayload,
    CsvCell,
    ModelCasePayload,
)

from .csv_adapter import CSV_PROJECTION_POLICY


def project_case(
    *,
    case: CommonCasePayload,
    model_case: ModelCasePayload,
    snapshot: LegacyPanelSnapshot,
    input_row: Mapping[str, CsvCell],
    run: LegacyRunContext,
    mode: CsvCell,
    speed_ratio: CsvCell,
    translational_temperature_k: CsvCell,
) -> LegacyPhase3Projection:
    """Preserve FMF-only CSV fields around common Phase 3 operations."""
    csv_values = run.csv_values()
    csv_values.update(
        {
            "mode": mode,
            "out_S": speed_ratio,
            "out_Ti_K": translational_temperature_k,
        }
    )
    artifact_policy = ArtifactProjectionPolicy(
        attitude_input_used=run.attitude_input_used,
        case_signature=run.case_signature,
        ray_backend_used=run.ray_backend_used,
        solver_version=run.solver_version,
    )
    return project_legacy_phase3_case(
        case=case,
        model_case=model_case,
        snapshot=snapshot,
        input_row=input_row,
        csv_policy=CSV_PROJECTION_POLICY,
        csv_run_values=csv_values,
        artifact_policy=artifact_policy,
    )


__all__ = ("project_case",)
