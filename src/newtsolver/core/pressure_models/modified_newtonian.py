"""Modified-Newtonian compatibility callable."""

from panelsolver.models.hypersonic.modified_newtonian import (
    modified_newtonian_cp_max as _shared_modified_newtonian_cp_max,
)


def modified_newtonian_cp_max(Mach: "float", gamma: "float") -> "float":
    """Delegate the frozen public call to the shared pressure equation."""
    return _shared_modified_newtonian_cp_max(Mach, gamma)

__all__ = ("modified_newtonian_cp_max",)
