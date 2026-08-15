"""FMF shielding signature over the shared core engine."""

from panelsolver._compat.legacy_shielding import (
    clear_shielding_cache,
    compute_legacy_shield_mask,
    compute_legacy_shield_mask_with_backend,
)


def clear_shield_cache() -> None:
    clear_shielding_cache()


def compute_shield_mask(
    mesh,
    centers_m,
    Vhat,
    batch_size: int | None = None,
    ray_backend: str = "auto",
):
    return compute_legacy_shield_mask(
        mesh,
        centers_m,
        Vhat,
        batch_size,
        ray_backend,
        legacy_env_prefix="FMFSOLVER",
    )


def compute_shield_mask_with_backend(
    mesh,
    centers_m,
    Vhat,
    batch_size: int | None = None,
    ray_backend: str = "auto",
):
    return compute_legacy_shield_mask_with_backend(
        mesh,
        centers_m,
        Vhat,
        batch_size,
        ray_backend,
        legacy_env_prefix="FMFSOLVER",
    )


__all__ = (
    "clear_shield_cache",
    "compute_shield_mask",
    "compute_shield_mask_with_backend",
)
