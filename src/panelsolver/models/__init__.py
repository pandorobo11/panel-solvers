"""Independent physical load models and their explicit assembly registry."""

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
    "SENTMAN_ALGORITHM_VERSION",
    "SENTMAN_MODEL_ID",
    "DuplicateModelError",
    "ModelCaseMismatchError",
    "ModelOutputError",
    "ModelRegistry",
    "ModelRegistryError",
    "ResolvedSentmanCase",
    "SentmanCaseError",
    "SentmanModel",
    "UnknownModelError",
    "altitude_range_km",
    "mean_to_most_probable_speed",
    "resolve_sentman_case",
    "sample_at_altitude_km",
)
