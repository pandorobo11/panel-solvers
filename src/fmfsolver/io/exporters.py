"""Frozen FMF artifact calls over shared serializers."""

from __future__ import annotations

import numpy as np

from panelsolver.app.artifact_io import (
    write_legacy_npz,
    write_legacy_vtp,
)


def export_vtp(
    out_path: str,
    vertices: np.ndarray,
    faces: np.ndarray,
    cell_data: dict,
    field_data: dict | None = None,
):
    """Write face-based solver outputs as a VTP PolyData file."""
    write_legacy_vtp(out_path, vertices, faces, cell_data, field_data)


def export_npz(out_path: str, **arrays):
    """Write multiple named arrays into a compressed NPZ file."""
    write_legacy_npz(out_path, **arrays)


__all__ = ("export_npz", "export_vtp")
