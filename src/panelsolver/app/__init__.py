"""Shared command-line and graphical application layer."""

from .csv_writer import (
    AtomicCsvWritePolicy,
    TempNameStyle,
    validate_csv_output_path,
    write_csv_atomic,
)
from .execution import default_model_registry, request_from_registry
from .legacy_adapter import (
    AdaptedLegacyPanels,
    LegacyPanelSnapshot,
    LegacyPhase3Projection,
    LegacyRunContext,
    adapt_legacy_panels,
    project_legacy_phase3_case,
)

__all__ = (
    "AdaptedLegacyPanels",
    "AtomicCsvWritePolicy",
    "LegacyPanelSnapshot",
    "LegacyPhase3Projection",
    "LegacyRunContext",
    "TempNameStyle",
    "adapt_legacy_panels",
    "default_model_registry",
    "project_legacy_phase3_case",
    "request_from_registry",
    "validate_csv_output_path",
    "write_csv_atomic",
)
