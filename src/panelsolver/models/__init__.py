"""Independent physical load models and their explicit assembly registry."""

from .hypersonic import (
    HYPERSONIC_ALGORITHM_VERSION,
    HYPERSONIC_MODEL_ID,
    HypersonicCaseError,
    HypersonicModel,
    ResolvedHypersonicCase,
    resolve_hypersonic_case,
)
from .registry import (
    DuplicateModelError,
    ModelCaseMismatchError,
    ModelOutputError,
    ModelRegistry,
    ModelRegistryError,
    UnknownModelError,
)
from .sentman import (
    SENTMAN_ALGORITHM_VERSION,
    SENTMAN_MODEL_ID,
    ResolvedSentmanCase,
    SentmanCaseError,
    SentmanModel,
    resolve_sentman_case,
)
from .sentman_atmosphere import (
    altitude_range_km,
    mean_to_most_probable_speed,
    sample_at_altitude_km,
)

__all__ = (
    "HYPERSONIC_ALGORITHM_VERSION",
    "HYPERSONIC_MODEL_ID",
    "SENTMAN_ALGORITHM_VERSION",
    "SENTMAN_MODEL_ID",
    "DuplicateModelError",
    "HypersonicCaseError",
    "HypersonicModel",
    "ModelCaseMismatchError",
    "ModelOutputError",
    "ModelRegistry",
    "ModelRegistryError",
    "ResolvedHypersonicCase",
    "ResolvedSentmanCase",
    "SentmanCaseError",
    "SentmanModel",
    "UnknownModelError",
    "altitude_range_km",
    "mean_to_most_probable_speed",
    "resolve_hypersonic_case",
    "resolve_sentman_case",
    "sample_at_altitude_km",
)
