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


__all__ = ("write_npz_projection", "write_vtp_projection")
