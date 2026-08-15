"""Legacy trimesh shielding calls adapted to the shared panel contract."""

from __future__ import annotations

import numpy as np
import trimesh

from panelsolver.core import (
    MeshComponent,
    PanelGeometry,
    PanelMesh,
    ShieldingConfig,
    clear_shielding_cache,
    compute_shielding,
)

from .environment import resolve_shielding_environment


def _panel_mesh(mesh: trimesh.Trimesh, centers_m: np.ndarray) -> PanelMesh:
    centers = np.asarray(centers_m, dtype=np.float64)
    n_faces = len(mesh.faces)
    return PanelMesh(
        vertices_stl_m=np.asarray(mesh.vertices, dtype=np.float64),
        faces=np.asarray(mesh.faces, dtype=np.int64),
        geometry=PanelGeometry(
            centers_stl_m=centers,
            normals_out_stl=np.asarray(mesh.face_normals, dtype=np.float64),
            areas_m2=np.asarray(mesh.area_faces, dtype=np.float64),
            component_ids=np.zeros(n_faces, dtype=np.int64),
        ),
        components=(MeshComponent(0, "legacy-trimesh"),),
    )


def compute_legacy_shield_mask_with_backend(
    mesh: trimesh.Trimesh,
    centers_m: np.ndarray,
    Vhat: np.ndarray,
    batch_size: int | None = None,
    ray_backend: str = "auto",
    *,
    legacy_env_prefix: str,
) -> tuple[np.ndarray, str]:
    """Return the pinned tuple while retaining product environment policy."""
    result = compute_shielding(
        _panel_mesh(mesh, centers_m),
        np.asarray(Vhat, dtype=np.float64),
        resolve_shielding_environment(
            ShieldingConfig(
                ray_backend=ray_backend,
                batch_size=batch_size,
            ),
            legacy_env_prefix=legacy_env_prefix,
        ),
    )
    return np.array(result.shielded, copy=True), result.config.effective_backend


def compute_legacy_shield_mask(
    mesh: trimesh.Trimesh,
    centers_m: np.ndarray,
    Vhat: np.ndarray,
    batch_size: int | None = None,
    ray_backend: str = "auto",
    *,
    legacy_env_prefix: str,
) -> np.ndarray:
    """Mask-only compatibility form."""
    mask, _backend = compute_legacy_shield_mask_with_backend(
        mesh,
        centers_m,
        Vhat,
        batch_size,
        ray_backend,
        legacy_env_prefix=legacy_env_prefix,
    )
    return mask


__all__ = (
    "clear_shielding_cache",
    "compute_legacy_shield_mask",
    "compute_legacy_shield_mask_with_backend",
)
