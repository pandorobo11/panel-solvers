"""Frozen FMF case signature call."""

from panelsolver.app.legacy_signatures import build_legacy_case_signature

from ..case_adapter import LEGACY_SIGNATURE_POLICY


def build_case_signature(row: dict) -> str:
    return build_legacy_case_signature(row, LEGACY_SIGNATURE_POLICY)


__all__ = ("build_case_signature",)
