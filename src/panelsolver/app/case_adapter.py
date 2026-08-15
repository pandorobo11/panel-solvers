"""Product-policy adaptation from normalized rows to shared execution inputs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np

from panelsolver.core import (
    CaseExecutionRequest,
    CommonCasePayload,
    MeshValidationPolicy,
    ModelCasePayload,
    ShieldingConfig,
    prepare_case_signature,
)
from panelsolver.models import ModelRegistry

from .attitude import ResolvedAttitude, resolve_attitude
from .environment import resolve_shielding_environment
from .execution import default_model_registry, request_from_registry
from .legacy_signatures import (
    LegacySignaturePolicy,
    build_legacy_signature_candidates,
)
from .solver_spec import ArtifactSignatureCandidates

type ModelPayloadBuilder = Callable[[Mapping[str, object]], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class ProductCasePolicy:
    """Independent FMF/newtsolver choices needed at the execution boundary."""

    product_id: str
    model_id: str
    compatibility_version: str
    legacy_env_prefix: str
    mesh_validation_policy: MeshValidationPolicy
    signature_defaults: Mapping[str, object]
    legacy_signature_policy: LegacySignaturePolicy
    model_payload: ModelPayloadBuilder

    def __post_init__(self) -> None:
        if self.legacy_env_prefix not in {"FMFSOLVER", "NEWTSOLVER"}:
            raise ValueError("legacy_env_prefix is invalid")
        if not isinstance(self.mesh_validation_policy, MeshValidationPolicy):
            raise TypeError("mesh_validation_policy must be MeshValidationPolicy")
        if not callable(self.model_payload):
            raise TypeError("model_payload must be callable")
        if self.legacy_signature_policy.compatibility_version != (
            self.compatibility_version
        ):
            raise ValueError("legacy and product compatibility versions must match")


@dataclass(frozen=True, slots=True)
class AdaptedCase:
    """A normalized product row bound to one model-neutral execution request."""

    request: CaseExecutionRequest
    attitude: ResolvedAttitude

    def __post_init__(self) -> None:
        if not isinstance(self.request, CaseExecutionRequest):
            raise TypeError("request must be a CaseExecutionRequest")
        if not isinstance(self.attitude, ResolvedAttitude):
            raise TypeError("attitude must be a ResolvedAttitude")


def _stl_paths(row: Mapping[str, object]) -> tuple[str, ...]:
    paths = tuple(
        part.strip() for part in str(row.get("stl_path", "")).split(";") if part.strip()
    )
    if not paths:
        raise ValueError("stl_path has no valid entry")
    return paths


def adapt_case_row(
    row: Mapping[str, object],
    policy: ProductCasePolicy,
    *,
    registry: ModelRegistry | None = None,
) -> AdaptedCase:
    """Translate one already-normalized product row without executing a model."""
    if not isinstance(row, Mapping):
        raise TypeError("row must be a mapping")
    if not isinstance(policy, ProductCasePolicy):
        raise TypeError("policy must be a ProductCasePolicy")
    attitude = resolve_attitude(
        float(row["alpha_deg"]),
        float(row["beta_or_bank_deg"]),
        row.get("attitude_input"),
    )
    common_case = CommonCasePayload(
        case_id=str(row["case_id"]),
        Aref_m2=float(row["Aref_m2"]),
        moment_reference_stl_m=np.asarray(
            [row["ref_x_m"], row["ref_y_m"], row["ref_z_m"]],
            dtype=np.float64,
        ),
        Lref_Cl_m=float(row["Lref_Cl_m"]),
        Lref_Cm_m=float(row["Lref_Cm_m"]),
        Lref_Cn_m=float(row["Lref_Cn_m"]),
        alpha_t_deg=attitude.alpha_t_deg,
        beta_t_deg=attitude.beta_t_deg,
    )
    model_case = ModelCasePayload(
        model_id=policy.model_id,
        payload=policy.model_payload(row),
    )
    selected_registry = default_model_registry() if registry is None else registry
    request = request_from_registry(
        selected_registry,
        common_case=common_case,
        model_case=model_case,
        stl_paths=_stl_paths(row),
        scale_m_per_unit=float(row["stl_scale_m_per_unit"]),
        velocity_hat_stl=attitude.velocity_hat_stl,
        shielding=resolve_shielding_environment(
            ShieldingConfig(
                enabled=bool(int(row.get("shielding_on", 0))),
                ray_backend=str(row.get("ray_backend", "auto")),
            ),
            legacy_env_prefix=policy.legacy_env_prefix,
        ),
        mesh_validation_policy=policy.mesh_validation_policy,
    )
    return AdaptedCase(request, attitude)


def build_artifact_signature_candidates(
    row: Mapping[str, object],
    policy: ProductCasePolicy,
    *,
    registry: ModelRegistry | None = None,
) -> ArtifactSignatureCandidates:
    """Build primary execution identity followed by opaque pinned fallbacks."""
    adapted = adapt_case_row(row, policy, registry=registry)
    primary = prepare_case_signature(adapted.request)
    legacy = build_legacy_signature_candidates(
        row,
        defaults=policy.signature_defaults,
        policy=policy.legacy_signature_policy,
    )
    return ArtifactSignatureCandidates(primary, legacy)


__all__ = (
    "AdaptedCase",
    "ModelPayloadBuilder",
    "ProductCasePolicy",
    "adapt_case_row",
    "build_artifact_signature_candidates",
)
