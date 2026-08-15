"""Legacy FMF runtime surface delegating to canonical domain composition."""

from dataclasses import replace

from panelsolver.domains.fmf import (
    GUI_ADAPTERS as _CANONICAL_GUI_ADAPTERS,
)
from panelsolver.domains.fmf import (
    RUNTIME_POLICY,
    run_cases,
)

from .case_adapter import build_signatures

GUI_ADAPTERS = replace(
    _CANONICAL_GUI_ADAPTERS,
    build_case_signatures=build_signatures,
)

__all__ = ("GUI_ADAPTERS", "RUNTIME_POLICY", "run_cases")
