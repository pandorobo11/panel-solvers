"""Thin Phase 3 adapters for already-computed legacy panel data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from panelsolver.core import (
    ArtifactProjectionPolicy,
    CommonCasePayload,
    CommonResults,
    CsvCell,
    CsvProjection,
    CsvProjectionPolicy,
    LocalLoads,
    MeshComponent,
    ModelCasePayload,
    PanelFlowState,
    PanelGeometry,
    PanelMesh,
    PayloadValue,
    VtpProjection,
    assemble_common_results,
    project_summary_csv,
    project_vtp_artifact,
    velocity_hat_stl_from_tangent_angles,
)


@dataclass(slots=True)
class LegacyPanelSnapshot:
    """Transient data copied from a legacy pipeline after model evaluation.

    The snapshot deliberately contains no model equation or filesystem action.
    Core contract constructors make immutable copies during adaptation.
    """

    vertices_stl_m: object
    faces: object
    centers_stl_m: object
    normals_out_stl: object
    areas_m2: object
    component_ids: object
    component_sources: Sequence[str]
    shielded: object
    traction_coeff_stl: object
    cell_scalars: Mapping[str, object] = field(default_factory=dict)
    load_metadata: Mapping[str, PayloadValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, eq=False)
class AdaptedLegacyPanels:
    """Validated mesh, flow state, and local loads produced by the thin adapter."""

    mesh: PanelMesh
    flow_state: PanelFlowState
    local_loads: LocalLoads


@dataclass(frozen=True, slots=True)
class LegacyRunContext:
    """Run metadata shared by CSV and artifact projection policies."""

    attitude_input_used: str
    case_signature: str
    ray_backend_used: str
    solver_version: str
    run_started_at_utc: CsvCell
    run_finished_at_utc: CsvCell
    run_elapsed_s: CsvCell
    vtp_path: CsvCell

    def csv_values(self) -> dict[str, CsvCell]:
        return {
            "solver_version": self.solver_version,
            "case_signature": self.case_signature,
            "run_started_at_utc": self.run_started_at_utc,
            "run_finished_at_utc": self.run_finished_at_utc,
            "run_elapsed_s": self.run_elapsed_s,
            "out_attitude_input": self.attitude_input_used,
            "ray_backend_used": self.ray_backend_used,
            "vtp_path": self.vtp_path,
        }


@dataclass(frozen=True, slots=True, eq=False)
class LegacyPhase3Projection:
    """One adapter pass through all extracted Phase 3 operations."""

    mesh: PanelMesh
    results: CommonResults
    csv: CsvProjection
    vtp: VtpProjection


def adapt_legacy_panels(
    case: CommonCasePayload,
    snapshot: LegacyPanelSnapshot,
) -> AdaptedLegacyPanels:
    """Copy already-computed legacy panel data into Phase 2/3 contracts."""
    if not isinstance(case, CommonCasePayload):
        raise TypeError("case must be a CommonCasePayload")
    if not isinstance(snapshot, LegacyPanelSnapshot):
        raise TypeError("snapshot must be a LegacyPanelSnapshot")
    geometry = PanelGeometry(
        centers_stl_m=snapshot.centers_stl_m,
        normals_out_stl=snapshot.normals_out_stl,
        areas_m2=snapshot.areas_m2,
        component_ids=snapshot.component_ids,
    )
    mesh = PanelMesh(
        snapshot.vertices_stl_m,
        snapshot.faces,
        geometry,
        tuple(
            MeshComponent(component_id, source)
            for component_id, source in enumerate(snapshot.component_sources)
        ),
    )
    flow_state = PanelFlowState(
        velocity_hat_stl_from_tangent_angles(
            case.alpha_t_deg,
            case.beta_t_deg,
        ),
        snapshot.shielded,
    )
    local_loads = LocalLoads(
        snapshot.traction_coeff_stl,
        snapshot.cell_scalars,
        snapshot.load_metadata,
    )
    return AdaptedLegacyPanels(mesh, flow_state, local_loads)


def project_legacy_phase3_case(
    *,
    case: CommonCasePayload,
    model_case: ModelCasePayload,
    snapshot: LegacyPanelSnapshot,
    input_row: Mapping[str, CsvCell],
    csv_policy: CsvProjectionPolicy,
    csv_run_values: Mapping[str, CsvCell],
    artifact_policy: ArtifactProjectionPolicy,
    result_metadata: Mapping[str, PayloadValue] | None = None,
    component_metadata: Mapping[int, Mapping[str, PayloadValue]] | None = None,
) -> LegacyPhase3Projection:
    """Route one computed legacy case through every extracted Phase 3 layer."""
    adapted = adapt_legacy_panels(case, snapshot)
    results = assemble_common_results(
        case,
        model_case,
        adapted.mesh.geometry,
        adapted.flow_state,
        adapted.local_loads,
        metadata=result_metadata,
        metadata_by_component=component_metadata,
    )
    component_sources = {
        component.component_id: component.source
        for component in adapted.mesh.components
    }
    csv_projection = project_summary_csv(
        input_row,
        results,
        csv_policy,
        run_values=csv_run_values,
        component_sources=component_sources,
    )
    vtp_projection = project_vtp_artifact(
        adapted.mesh,
        results,
        artifact_policy,
    )
    return LegacyPhase3Projection(
        adapted.mesh,
        results,
        csv_projection,
        vtp_projection,
    )


__all__ = (
    "AdaptedLegacyPanels",
    "LegacyPanelSnapshot",
    "LegacyPhase3Projection",
    "LegacyRunContext",
    "adapt_legacy_panels",
    "project_legacy_phase3_case",
)
