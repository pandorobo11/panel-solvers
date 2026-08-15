"""Stable high-level in-memory API for the shared panel-solver platform."""

from panelsolver.app.attitude import ResolvedAttitude, resolve_attitude

from .api import (
    FMFCase,
    HypersonicCase,
    SolveResult,
    solve_fmf,
    solve_hypersonic,
)

__all__ = (
    "FMFCase",
    "HypersonicCase",
    "ResolvedAttitude",
    "SolveResult",
    "resolve_attitude",
    "solve_fmf",
    "solve_hypersonic",
)
