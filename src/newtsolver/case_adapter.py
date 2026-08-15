"""newtsolver schema/signature policy for shared row adaptation."""

from __future__ import annotations

from collections.abc import Mapping

from panelsolver._compat.legacy_signatures import (
    LegacySignaturePolicy,
    build_artifact_signature_candidates,
)
from panelsolver.app.case_adapter import (
    AdaptedCase,
    ProductCasePolicy,
    adapt_case_row,
)
from panelsolver.app.case_io import expand_component_values
from panelsolver.app.solver_spec import ArtifactSignatureCandidates
from panelsolver.core import MeshValidationPolicy, prepare_case_signature
from panelsolver.models import ModelRegistry
from panelsolver.models.hypersonic.selectors import (
    normalize_leeward_equation,
    normalize_windward_equation,
)

from ._version import NEWTSOLVER_COMPATIBILITY_VERSION
from .io.io_cases import DEFAULTS

_SIGNATURE_KEYS = (
    "case_id",
    "stl_path",
    "stl_scale_m_per_unit",
    "Mach",
    "gamma",
    "windward_eq",
    "leeward_eq",
    "alpha_deg",
    "beta_or_bank_deg",
    "attitude_input",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
    "shielding_on",
    "ray_backend",
)
_NUMERIC_SIGNATURE_KEYS = frozenset(
    {
        "stl_scale_m_per_unit",
        "Mach",
        "gamma",
        "alpha_deg",
        "beta_or_bank_deg",
        "ref_x_m",
        "ref_y_m",
        "ref_z_m",
        "Aref_m2",
        "Lref_Cl_m",
        "Lref_Cm_m",
        "Lref_Cn_m",
        "shielding_on",
    }
)


def _canonical_or_raw(
    value: object,
    *,
    default: str,
    field: str,
    component_count: int,
    resolver,
) -> str:
    try:
        _, canonical = expand_component_values(
            value,
            default_value=default,
            resolver=resolver,
            component_count=component_count,
            field_name=field,
        )
        return canonical
    except Exception:
        raw = str(value or "").strip().lower()
        return raw or default


def _adapt_legacy_payload(
    data: dict[str, object],
    row: Mapping[str, object],
    paths: tuple[str, ...],
) -> None:
    component_count = max(len(paths), 1)
    data["windward_eq"] = _canonical_or_raw(
        row.get("windward_eq"),
        default="newtonian",
        field="windward_eq",
        component_count=component_count,
        resolver=normalize_windward_equation,
    )
    data["leeward_eq"] = _canonical_or_raw(
        row.get("leeward_eq"),
        default="shield",
        field="leeward_eq",
        component_count=component_count,
        resolver=normalize_leeward_equation,
    )


def _model_payload(row: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "Mach": float(row["Mach"]),
        "gamma": float(row["gamma"]),
        "windward_eq": str(row.get("windward_eq", "newtonian")),
        "leeward_eq": str(row.get("leeward_eq", "shield")),
    }


LEGACY_SIGNATURE_POLICY = LegacySignaturePolicy(
    keys=_SIGNATURE_KEYS,
    numeric_keys=_NUMERIC_SIGNATURE_KEYS,
    compatibility_version=NEWTSOLVER_COMPATIBILITY_VERSION,
    file_identity_style="newtsolver",
    adapt_payload=_adapt_legacy_payload,
)
CASE_POLICY = ProductCasePolicy(
    product_id="newtsolver",
    model_id="hypersonic",
    compatibility_version=NEWTSOLVER_COMPATIBILITY_VERSION,
    legacy_env_prefix="NEWTSOLVER",
    mesh_validation_policy=MeshValidationPolicy.STRICT,
    model_payload=_model_payload,
)


def adapt_row(
    row: Mapping[str, object],
    *,
    registry: ModelRegistry | None = None,
) -> AdaptedCase:
    return adapt_case_row(row, CASE_POLICY, registry=registry)


def build_signatures(
    row: Mapping[str, object],
    *,
    registry: ModelRegistry | None = None,
) -> ArtifactSignatureCandidates:
    primary = prepare_case_signature(adapt_row(row, registry=registry).request)
    return build_artifact_signature_candidates(
        row,
        primary=primary,
        defaults=DEFAULTS,
        policy=LEGACY_SIGNATURE_POLICY,
    )


__all__ = (
    "CASE_POLICY",
    "LEGACY_SIGNATURE_POLICY",
    "NEWTSOLVER_COMPATIBILITY_VERSION",
    "adapt_row",
    "build_signatures",
)
