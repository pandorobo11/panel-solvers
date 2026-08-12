"""Frozen newtsolver case signature call."""

from dataclasses import replace

from panelsolver.app.legacy_signatures import build_legacy_case_signature

from ..case_adapter import LEGACY_SIGNATURE_POLICY, NEWTSOLVER_COMPATIBILITY_VERSION

SOLVER_VERSION = NEWTSOLVER_COMPATIBILITY_VERSION


def build_case_signature(row: dict) -> str:
    return build_legacy_case_signature(
        row,
        replace(LEGACY_SIGNATURE_POLICY, compatibility_version=SOLVER_VERSION),
    )


__all__ = ("SOLVER_VERSION", "build_case_signature")
