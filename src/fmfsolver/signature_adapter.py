"""Best-effort FMF legacy signature assembly, loaded only when requested."""

from __future__ import annotations

from collections.abc import Mapping

from panelsolver._compat.legacy_signatures import (
    LegacySignaturePolicy,
    build_artifact_signature_candidates,
)
from panelsolver.app.solver_spec import ArtifactSignatureCandidates
from panelsolver.core import prepare_case_signature
from panelsolver.models import ModelRegistry

from ._version import FMFSOLVER_COMPATIBILITY_VERSION
from .case_adapter import (
    _NUMERIC_SIGNATURE_KEYS,
    _SIGNATURE_KEYS,
    _no_legacy_payload_change,
    adapt_row,
)
from .io.io_cases import DEFAULTS

LEGACY_SIGNATURE_POLICY = LegacySignaturePolicy(
    keys=_SIGNATURE_KEYS,
    numeric_keys=_NUMERIC_SIGNATURE_KEYS,
    compatibility_version=FMFSOLVER_COMPATIBILITY_VERSION,
    file_identity_style="fmf",
    signature_schema_version=2,
    adapt_payload=_no_legacy_payload_change,
)


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


__all__ = ("LEGACY_SIGNATURE_POLICY", "build_signatures")
