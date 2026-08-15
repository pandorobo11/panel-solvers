"""Legacy mutable mesh views over the shared immutable mesh loader."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

from panelsolver.core import (
    MeshCacheStats,
    MeshValidationPolicy,
    clear_mesh_cache,
    load_panel_mesh,
    mesh_cache_stats,
)


@dataclass
class LegacyMeshData:
    """Frozen legacy field names backed by a fresh mutable mesh view."""

    mesh: trimesh.Trimesh
    centers_m: np.ndarray
    normals_out: np.ndarray
    areas_m2: np.ndarray
    face_stl_index: np.ndarray
    stl_paths_order: tuple[str, ...]


def load_legacy_meshes(
    stl_paths: list[str],
    scale_m_per_unit: float,
    logfn,
    *,
    validation_policy: MeshValidationPolicy,
) -> LegacyMeshData:
    """Translate a shared loaded mesh to the pinned mutable return shape."""
    loaded = load_panel_mesh(
        stl_paths,
        scale_m_per_unit,
        validation_policy=validation_policy,
        warning_callback=logfn,
    )
    panel_mesh = loaded.mesh
    mesh = trimesh.Trimesh(
        vertices=np.array(panel_mesh.vertices_stl_m, copy=True),
        faces=np.array(panel_mesh.faces, copy=True),
        process=False,
    )
    return LegacyMeshData(
        mesh=mesh,
        centers_m=np.array(panel_mesh.geometry.centers_stl_m, copy=True),
        normals_out=np.array(panel_mesh.geometry.normals_out_stl, copy=True),
        areas_m2=np.array(panel_mesh.geometry.areas_m2, copy=True),
        face_stl_index=np.asarray(
            panel_mesh.geometry.component_ids, dtype=np.int32
        ).copy(),
        stl_paths_order=tuple(component.source for component in panel_mesh.components),
    )


def clear_legacy_mesh_cache(reset_stats: bool = True) -> None:
    """Accept the legacy positional flag while using the shared cache."""
    clear_mesh_cache(reset_stats=reset_stats)


__all__ = (
    "LegacyMeshData",
    "MeshCacheStats",
    "clear_legacy_mesh_cache",
    "load_legacy_meshes",
    "mesh_cache_stats",
)
