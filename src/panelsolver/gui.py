"""Canonical GUI dispatcher using flow-domain names."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import replace

from fmfsolver.gui_spec import solver_spec as _fmf_compatibility_spec
from newtsolver.gui_spec import solver_spec as _hypersonic_compatibility_spec
from panelsolver.app.gui_bootstrap import run_gui
from panelsolver.app.solver_spec import SolverSpec

_DOMAIN_SPECS: dict[str, tuple[Callable[[], SolverSpec], str]] = {
    "fmf": (_fmf_compatibility_spec, "Panel Solver — FMF"),
    "hypersonic": (
        _hypersonic_compatibility_spec,
        "Panel Solver — Hypersonic",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the canonical GUI flow-domain selector parser."""
    parser = argparse.ArgumentParser(
        prog="panelsolver-gui",
        description="Launch the panel-solvers GUI for a canonical flow domain.",
    )
    subparsers = parser.add_subparsers(dest="domain", metavar="{fmf,hypersonic}")
    subparsers.add_parser(
        "fmf",
        help="Free-molecular-flow domain using the Sentman model",
    )
    subparsers.add_parser(
        "hypersonic",
        help="Hypersonic domain using Newtonian-family panel methods",
    )
    return parser


def canonical_gui_spec(domain: str) -> SolverSpec:
    """Return a domain-identified view of one existing GUI composition policy."""
    try:
        factory, title = _DOMAIN_SPECS[domain]
    except KeyError as exc:
        raise ValueError(f"unknown flow domain: {domain!r}") from exc
    return replace(factory(), product_id=domain, window_title=title)


def main(argv: list[str] | None = None) -> int:
    """Select a flow domain and launch the existing shared GUI shell."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not arguments:
        parser.print_help()
        return 0
    namespace = parser.parse_args(arguments)
    if namespace.domain is None:
        parser.error("a flow domain is required: fmf or hypersonic")
    return run_gui(canonical_gui_spec(namespace.domain), argv=[sys.argv[0]])


__all__ = ("build_parser", "canonical_gui_spec", "main")
