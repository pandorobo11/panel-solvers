"""Installed distribution version used for runtime artifact provenance."""

from importlib.metadata import version

_DISTRIBUTION_NAME = "panel-solvers"


def panel_solvers_distribution_version() -> str:
    """Return the installed panel-solvers distribution version."""
    return version(_DISTRIBUTION_NAME)


__all__ = ("panel_solvers_distribution_version",)
