"""FMF schema/signature policy for shared row adaptation."""

from __future__ import annotations

from collections.abc import Mapping

from panelsolver.app.case_adapter import (
    AdaptedCase,
    ProductCasePolicy,
    adapt_case_row,
    build_artifact_signature_candidates,
)
from panelsolver.app.case_io import is_filled
from panelsolver.app.legacy_signatures import LegacySignaturePolicy
from panelsolver.app.solver_spec import ArtifactSignatureCandidates
from panelsolver.core import MeshValidationPolicy
from panelsolver.models import ModelRegistry

from .io.io_cases import DEFAULTS

FMFSOLVER_COMPATIBILITY_VERSION = "1.3.8"

_SIGNATURE_KEYS = (
    "case_id",
    "stl_path",
    "stl_scale_m_per_unit",
    "alpha_deg",
    "beta_or_bank_deg",
    "attitude_input",
    "Tw_K",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
    "S",
    "Ti_K",
    "Mach",
    "Altitude_km",
    "shielding_on",
    "ray_backend",
)
_NUMERIC_SIGNATURE_KEYS = frozenset(
    {
        "stl_scale_m_per_unit",
        "alpha_deg",
        "beta_or_bank_deg",
        "Tw_K",
        "ref_x_m",
        "ref_y_m",
        "ref_z_m",
        "Aref_m2",
        "Lref_Cl_m",
        "Lref_Cm_m",
        "Lref_Cn_m",
        "S",
        "Ti_K",
        "Mach",
        "Altitude_km",
        "shielding_on",
    }
)


def _no_legacy_payload_change(
    _data: dict[str, object],
    _row: Mapping[str, object],
    _paths: tuple[str, ...],
) -> None:
    return None


def _optional_number(row: Mapping[str, object], name: str) -> float | None:
    value = row.get(name)
    return float(value) if is_filled(value) else None


def _model_payload(row: Mapping[str, object]) -> Mapping[str, object]:
    return {
        "S": _optional_number(row, "S"),
        "Ti_K": _optional_number(row, "Ti_K"),
        "Mach": _optional_number(row, "Mach"),
        "Altitude_km": _optional_number(row, "Altitude_km"),
        "Tw_K": float(row["Tw_K"]),
    }


LEGACY_SIGNATURE_POLICY = LegacySignaturePolicy(
    keys=_SIGNATURE_KEYS,
    numeric_keys=_NUMERIC_SIGNATURE_KEYS,
    compatibility_version=FMFSOLVER_COMPATIBILITY_VERSION,
    file_identity_style="fmf",
    signature_schema_version=2,
    adapt_payload=_no_legacy_payload_change,
)
CASE_POLICY = ProductCasePolicy(
    product_id="fmfsolver",
    model_id="sentman",
    compatibility_version=FMFSOLVER_COMPATIBILITY_VERSION,
    legacy_env_prefix="FMFSOLVER",
    mesh_validation_policy=MeshValidationPolicy.STRICT,
    strict_beta_tan_domain=True,
    signature_defaults=DEFAULTS,
    legacy_signature_policy=LEGACY_SIGNATURE_POLICY,
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
    return build_artifact_signature_candidates(row, CASE_POLICY, registry=registry)


__all__ = (
    "CASE_POLICY",
    "FMFSOLVER_COMPATIBILITY_VERSION",
    "LEGACY_SIGNATURE_POLICY",
    "adapt_row",
    "build_signatures",
)
