"""Canonical command dispatcher for the shared panel-solver platform."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from fmfsolver.app.cli_app import CLI_POLICY as _FMF_POLICY
from newtsolver.app.cli_app import CLI_POLICY as _HYPERSONIC_POLICY
from panelsolver.app.cli import ProductCliPolicy, run_cli

_POLICIES: dict[str, ProductCliPolicy] = {
    "fmf": replace(
        _FMF_POLICY,
        program="panelsolver fmf",
        description=(
            "Run the Sentman free-molecular-flow model from CSV/XLSX/XLSM input."
        ),
    ),
    "hypersonic": replace(
        _HYPERSONIC_POLICY,
        program="panelsolver hypersonic",
        description="Run hypersonic panel models from CSV/XLSX/XLSM input.",
    ),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the small model-domain selector parser."""
    parser = argparse.ArgumentParser(
        prog="panelsolver",
        description="Run panel-solvers using a canonical flow-domain selector.",
    )
    subparsers = parser.add_subparsers(dest="domain", metavar="{fmf,hypersonic}")
    subparsers.add_parser(
        "fmf",
        add_help=False,
        help="Sentman free-molecular-flow cases",
    )
    subparsers.add_parser(
        "hypersonic",
        add_help=False,
        help="Hypersonic panel-model cases",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Select a physical flow domain and reuse the shared batch CLI service."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not arguments:
        parser.print_help()
        return 0
    namespace, remaining = parser.parse_known_args(arguments)
    if namespace.domain is None:
        parser.error("a flow domain is required: fmf or hypersonic")
    return run_cli(_POLICIES[namespace.domain], remaining)


__all__ = ("build_parser", "main")
