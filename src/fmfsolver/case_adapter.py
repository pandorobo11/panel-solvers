"""Legacy FMF signature fallback around canonical case adaptation."""

from __future__ import annotations

import importlib
from collections.abc import Mapping

from panelsolver.app.solver_spec import ArtifactSignatureCandidates
from panelsolver.domains.fmf import CASE_POLICY, adapt_row
from panelsolver.models import ModelRegistry

from ._version import FMFSOLVER_COMPATIBILITY_VERSION

LEGACY_SIGNATURE_POLICY: object

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


def build_signatures(
    row: Mapping[str, object],
    *,
    registry: ModelRegistry | None = None,
) -> ArtifactSignatureCandidates:
    adapter = importlib.import_module(f"{__package__}.signature_adapter")
    return adapter.build_signatures(row, registry=registry)


def __getattr__(name: str):
    if name == "LEGACY_SIGNATURE_POLICY":
        adapter = importlib.import_module(f"{__package__}.signature_adapter")
        return adapter.LEGACY_SIGNATURE_POLICY
    raise AttributeError(name)


__all__ = (
    "CASE_POLICY",
    "FMFSOLVER_COMPATIBILITY_VERSION",
    "LEGACY_SIGNATURE_POLICY",
    "adapt_row",
    "build_signatures",
)
