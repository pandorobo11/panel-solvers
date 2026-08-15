"""Stable high-level in-memory API for the shared panel-solver platform."""

from panelsolver.app.attitude import ResolvedAttitude, resolve_attitude

from .api import (
    HypersonicCase,
    SentmanCase,
    SolveResult,
    solve_hypersonic,
    solve_sentman,
)

__all__ = (
    "HypersonicCase",
    "ResolvedAttitude",
    "SentmanCase",
    "SolveResult",
    "resolve_attitude",
    "solve_hypersonic",
    "solve_sentman",
)
