"""Filesystem serializers for validated semantic artifact projections."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv

from panelsolver.core import NpzProjection, VtpProjection


def write_vtp_projection(path: str | Path, projection: VtpProjection) -> Path:
    """Write one VTP projection with the pinned binary PolyData semantics."""
    if not isinstance(projection, VtpProjection):
        raise TypeError("projection must be a VtpProjection")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    poly = pv.PolyData(projection.points, projection.faces)
    for name, values in projection.cell_data.items():
        poly.cell_data[name] = np.asarray(values)
    for name, values in projection.field_data.items():
        poly.field_data[name] = np.asarray(values)
    poly.save(str(output), binary=True)
    return output


def write_npz_projection(path: str | Path, projection: NpzProjection) -> Path:
    """Write one compressed NPZ projection without changing named arrays."""
    if not isinstance(projection, NpzProjection):
        raise TypeError("projection must be an NpzProjection")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **dict(projection.arrays))
    return output


def write_legacy_vtp(
    path: str | Path,
    vertices: np.ndarray,
    faces: np.ndarray,
    cell_data: dict,
    field_data: dict | None = None,
) -> Path:
    """Serialize the frozen direct-array VTP call through the shared writer."""
    face_array = np.asarray(faces, dtype=np.int64)
    vtk_faces = np.hstack(
        (np.full((face_array.shape[0], 1), 3, dtype=np.int64), face_array)
    ).ravel()
    poly = pv.PolyData(np.asarray(vertices, dtype=float), vtk_faces)
    for name, values in cell_data.items():
        poly.cell_data[name] = np.asarray(values)
    for name, value in (field_data or {}).items():
        poly.field_data[name] = np.asarray([value])
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    poly.save(str(output), binary=True)
    return output


def write_legacy_npz(path: str | Path, **arrays) -> Path:
    """Serialize the frozen named-array NPZ call."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    return output


__all__ = (
    "write_legacy_npz",
    "write_legacy_vtp",
    "write_npz_projection",
    "write_vtp_projection",
)
