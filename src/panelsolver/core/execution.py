"""One-case model-neutral execution through the shared numerical pipeline."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from ._validation import (
    float_array,
    nonempty_text,
    real_scalar,
    validate_unit_vectors,
)
from .aggregation import assemble_common_results
from .contracts import (
    CommonCasePayload,
    CommonResults,
    LocalLoads,
    ModelCasePayload,
    PanelFlowState,
    PanelGeometry,
    PanelLoadModel,
)
from .errors import PanelSolverError
from .frames import velocity_hat_stl_from_tangent_angles
from .mesh import PanelMesh
from .mesh_loading import (
    MeshValidationPolicy,
    load_panel_mesh,
)
from .result_cache import ResultCache
from .shielding import ShieldingConfig, ShieldingResult, compute_shielding
from .signatures import CaseSignature, build_case_signature


class ExecutionError(PanelSolverError, ValueError):
    """Shared execution input or state is invalid."""


class ExecutionModelError(ExecutionError):
    """A model identity or output violates the execution boundary."""


@runtime_checkable
class ExecutablePanelLoadModel(PanelLoadModel, Protocol):
    """Phase 2 model plus its model-owned normalized signature payload."""

    def signature_payload(self, case: ModelCasePayload) -> Mapping[str, object]:
        """Return the normalized model-case portion of ADR 0005."""
        ...


@dataclass(frozen=True, slots=True, eq=False)
class CaseExecutionRequest:
    """Validated inputs required to execute exactly one numerical case."""

    model: ExecutablePanelLoadModel
    common_case: CommonCasePayload
    model_case: ModelCasePayload
    stl_paths: Sequence[str | Path]
    scale_m_per_unit: float
    velocity_hat_stl: np.ndarray
    shielding: ShieldingConfig = field(default_factory=ShieldingConfig)
    mesh_validation_policy: MeshValidationPolicy | str = MeshValidationPolicy.STRICT

    def __post_init__(self) -> None:
        if not isinstance(self.model, ExecutablePanelLoadModel):
            raise ExecutionModelError(
                "model must implement PanelLoadModel and signature_payload()"
            )
        if not isinstance(self.common_case, CommonCasePayload):
            raise TypeError("common_case must be a CommonCasePayload instance")
        if not isinstance(self.model_case, ModelCasePayload):
            raise TypeError("model_case must be a ModelCasePayload instance")
        try:
            model_id = nonempty_text(self.model.model_id, field="model.model_id")
            nonempty_text(
                self.model.algorithm_version,
                field="model.algorithm_version",
            )
        except PanelSolverError as exc:
            raise ExecutionModelError(str(exc)) from exc
        if self.model_case.model_id != model_id:
            raise ExecutionModelError(
                f"model_case model_id {self.model_case.model_id!r} does not match "
                f"model {model_id!r}"
            )

        if isinstance(self.stl_paths, (str, bytes, Path)):
            raise ExecutionError("stl_paths must be a non-empty sequence of paths.")
        try:
            stl_paths = tuple(str(path) for path in self.stl_paths)
        except TypeError as exc:
            raise ExecutionError(
                "stl_paths must be a non-empty sequence of paths."
            ) from exc
        if not stl_paths or any(not path for path in stl_paths):
            raise ExecutionError("stl_paths must be a non-empty sequence of paths.")
        try:
            scale = real_scalar(
                self.scale_m_per_unit,
                field="scale_m_per_unit",
                positive=True,
            )
            velocity = float_array(
                self.velocity_hat_stl,
                field="velocity_hat_stl",
                shape=(3,),
            )
            validate_unit_vectors(velocity, field="velocity_hat_stl")
        except PanelSolverError as exc:
            raise ExecutionError(str(exc)) from exc
        expected_velocity = velocity_hat_stl_from_tangent_angles(
            self.common_case.alpha_t_deg,
            self.common_case.beta_t_deg,
        )
        if not np.allclose(velocity, expected_velocity, rtol=0.0, atol=1.0e-12):
            raise ExecutionError(
                "velocity_hat_stl must match the resolved common-case tangent angles."
            )
        if not isinstance(self.shielding, ShieldingConfig):
            raise TypeError("shielding must be a ShieldingConfig instance")
        try:
            validation_policy = MeshValidationPolicy(self.mesh_validation_policy)
        except (TypeError, ValueError) as exc:
            raise ExecutionError("mesh_validation_policy is invalid.") from exc

        object.__setattr__(self, "stl_paths", stl_paths)
        object.__setattr__(self, "scale_m_per_unit", scale)
        object.__setattr__(self, "velocity_hat_stl", velocity)
        object.__setattr__(self, "mesh_validation_policy", validation_policy)


@dataclass(frozen=True, slots=True, eq=False)
class CaseExecutionResult:
    """Complete one-case result before product artifact serialization."""

    mesh: PanelMesh
    shielding: ShieldingResult
    results: CommonResults
    signature: CaseSignature
    cache_hit: bool
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        expected = (
            ("mesh", self.mesh, PanelMesh),
            ("shielding", self.shielding, ShieldingResult),
            ("results", self.results, CommonResults),
            ("signature", self.signature, CaseSignature),
        )
        for name, value, expected_type in expected:
            if not isinstance(value, expected_type):
                raise ExecutionError(
                    f"{name} must be a {expected_type.__name__} instance."
                )
        if not isinstance(self.cache_hit, bool):
            raise ExecutionError("cache_hit must be a boolean.")
        warnings = tuple(self.warnings)
        if not all(isinstance(message, str) for message in warnings):
            raise ExecutionError("warnings must contain only strings.")
        if self.mesh.n_faces != self.results.geometry.n_faces:
            raise ExecutionError("mesh and results face counts must match.")
        if not np.array_equal(
            self.shielding.shielded,
            self.results.flow_state.shielded,
        ):
            raise ExecutionError("shielding and results masks must match.")
        object.__setattr__(self, "warnings", warnings)


def _model_identity(model: ExecutablePanelLoadModel) -> tuple[str, str]:
    try:
        return (
            nonempty_text(model.model_id, field="model.model_id"),
            nonempty_text(
                model.algorithm_version,
                field="model.algorithm_version",
            ),
        )
    except PanelSolverError as exc:
        raise ExecutionModelError(str(exc)) from exc


def _validated_model_output(
    model: ExecutablePanelLoadModel,
    geometry: PanelGeometry,
    flow_state: PanelFlowState,
    model_case: ModelCasePayload,
    identity: tuple[str, str],
) -> LocalLoads:
    loads = model.evaluate(geometry, flow_state, model_case)
    if _model_identity(model) != identity:
        raise ExecutionModelError("model identity changed during evaluation.")
    if not isinstance(loads, LocalLoads):
        raise ExecutionModelError("model must return a LocalLoads instance.")
    if loads.n_faces != geometry.n_faces:
        raise ExecutionModelError(
            f"model returned {loads.n_faces} panels; expected {geometry.n_faces}."
        )
    if np.any(loads.traction_coeff_stl[flow_state.shielded] != 0.0):
        raise ExecutionModelError(
            "model returned nonzero traction on ray-shielded panels."
        )
    return loads


def _rebind_cached_results(
    cached: CommonResults,
    request: CaseExecutionRequest,
    mesh: PanelMesh,
    flow_state: PanelFlowState,
    signature: CaseSignature,
) -> CommonResults:
    if cached.metadata.get("case_signature") != signature.digest:
        raise ExecutionError("cached result signature metadata is inconsistent.")
    return CommonResults(
        case=request.common_case,
        model_case=request.model_case,
        geometry=mesh.geometry,
        flow_state=flow_state,
        local_loads=cached.local_loads,
        total=cached.total,
        components=cached.components,
        metadata=cached.metadata,
    )


def execute_case(
    request: CaseExecutionRequest,
    *,
    result_cache: ResultCache[CommonResults] | None = None,
    warning_callback: Callable[[str], None] | None = None,
) -> CaseExecutionResult:
    """Execute one case without concrete-model branches or artifact writes."""
    if not isinstance(request, CaseExecutionRequest):
        raise TypeError("request must be a CaseExecutionRequest instance")
    if result_cache is not None and not isinstance(result_cache, ResultCache):
        raise TypeError("result_cache must be a ResultCache instance")

    identity = _model_identity(request.model)
    request.model.validate_case(request.model_case)
    model_signature_payload = request.model.signature_payload(request.model_case)
    if _model_identity(request.model) != identity:
        raise ExecutionModelError("model identity changed during case validation.")
    loaded = load_panel_mesh(
        request.stl_paths,
        request.scale_m_per_unit,
        validation_policy=request.mesh_validation_policy,
        warning_callback=warning_callback,
    )
    shielding = compute_shielding(
        loaded.mesh,
        request.velocity_hat_stl,
        request.shielding,
    )
    flow_state = PanelFlowState(request.velocity_hat_stl, shielding.shielded)
    signature = build_case_signature(
        geometry_fingerprint=loaded.geometry_fingerprint,
        common_case=request.common_case,
        model_id=identity[0],
        model_algorithm_version=identity[1],
        model_case_payload=model_signature_payload,
        shielding_config=shielding.config,
    )

    if result_cache is not None:
        cached = result_cache.get(signature)
        if cached is not None:
            rebound = _rebind_cached_results(
                cached,
                request,
                loaded.mesh,
                flow_state,
                signature,
            )
            return CaseExecutionResult(
                mesh=loaded.mesh,
                shielding=shielding,
                results=rebound,
                signature=signature,
                cache_hit=True,
                warnings=loaded.warnings,
            )

    loads = _validated_model_output(
        request.model,
        loaded.mesh.geometry,
        flow_state,
        request.model_case,
        identity,
    )
    metadata = {
        "case_signature": signature.digest,
        "geometry_fingerprint": loaded.geometry_fingerprint,
        "ray_backend_used": shielding.config.effective_backend,
        "shielding_algorithm_version": shielding.config.algorithm_version,
    }
    results = assemble_common_results(
        request.common_case,
        request.model_case,
        loaded.mesh.geometry,
        flow_state,
        loads,
        metadata=metadata,
    )
    if result_cache is not None:
        result_cache.put(signature, results)
    return CaseExecutionResult(
        mesh=loaded.mesh,
        shielding=shielding,
        results=results,
        signature=signature,
        cache_hit=False,
        warnings=loaded.warnings,
    )


__all__ = (
    "CaseExecutionRequest",
    "CaseExecutionResult",
    "ExecutablePanelLoadModel",
    "ExecutionError",
    "ExecutionModelError",
    "execute_case",
)
