"""Legacy newtsolver command identity over canonical Hypersonic CLI policy."""

from __future__ import annotations

from dataclasses import replace

from panelsolver.app.cli import build_parser as build_product_parser
from panelsolver.app.cli import run_cli
from panelsolver.domains.hypersonic import CANONICAL_CLI_POLICY

CLI_POLICY = replace(
    CANONICAL_CLI_POLICY,
    program="newtsolver-cli",
    description="Run newtsolver from CSV/XLSX/XLSM input without GUI.",
)


def build_parser():
    return build_product_parser(CLI_POLICY)


def main(argv: list[str] | None = None) -> int:
    return run_cli(CLI_POLICY, argv)


__all__ = ("build_parser", "main")
