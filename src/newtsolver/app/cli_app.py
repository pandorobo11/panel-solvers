"""newtsolver policy selector for the shared batch command."""

from __future__ import annotations

from panelsolver.app.cli import ProductCliPolicy, run_cli
from panelsolver.app.cli import build_parser as build_product_parser

from ..csv_adapter import validate_results_output_path
from ..io.io_cases import read_cases
from ..runtime import RUNTIME_POLICY

CLI_POLICY = ProductCliPolicy(
    program="newtsolver-cli",
    description="Run newtsolver from CSV/Excel input without GUI.",
    runtime_policy=RUNTIME_POLICY,
    read_cases=read_cases,
    validate_output_path=validate_results_output_path,
)


def build_parser():
    return build_product_parser(CLI_POLICY)


def main(argv: list[str] | None = None) -> int:
    return run_cli(CLI_POLICY, argv)


__all__ = ("build_parser", "main")
