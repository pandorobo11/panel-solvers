"""newtsolver mesh return-shape policy over the shared loader."""

from panelsolver.app.legacy_mesh import (
    LegacyMeshData as MeshData,
)
from panelsolver.app.legacy_mesh import (
    MeshCacheStats,
    clear_legacy_mesh_cache,
    load_legacy_meshes,
    mesh_cache_stats,
)
from panelsolver.core import MeshValidationPolicy


def clear_mesh_cache(reset_stats: bool = True) -> None:
    clear_legacy_mesh_cache(reset_stats)


def load_meshes(stl_paths: list[str], scale_m_per_unit: float, logfn) -> MeshData:
    return load_legacy_meshes(
        stl_paths,
        scale_m_per_unit,
        logfn,
        validation_policy=MeshValidationPolicy.LEGACY_WARN_REPAIR,
    )


__all__ = (
    "MeshCacheStats",
    "MeshData",
    "clear_mesh_cache",
    "load_meshes",
    "mesh_cache_stats",
)
