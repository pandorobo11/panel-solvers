"""Installed distribution version used for runtime artifact provenance."""

from importlib.metadata import version

_DISTRIBUTION_NAME = "panelsolver"


def panelsolver_distribution_version() -> str:
    """Return the installed panelsolver distribution version."""
    return version(_DISTRIBUTION_NAME)


__all__ = ("panelsolver_distribution_version",)
