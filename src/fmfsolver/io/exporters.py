"""Frozen FMF artifact calls over shared serializers."""

from panelsolver.app.artifact_io import (
    write_legacy_npz as export_npz,
)
from panelsolver.app.artifact_io import (
    write_legacy_vtp as export_vtp,
)

__all__ = ("export_npz", "export_vtp")
