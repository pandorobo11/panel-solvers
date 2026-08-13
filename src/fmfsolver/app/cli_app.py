"""FMF policy selector for the shared batch command."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from panelsolver.app.cli import ProductCliPolicy, run_cli
from panelsolver.app.cli import build_parser as build_product_parser

from ..io.io_cases import read_cases
from ..runtime import RUNTIME_POLICY


def _validate_output(
    output_path: str | Path,
    input_path: str | Path,
    _rows: Sequence[Mapping[str, object]],
) -> Path:
    return Path(output_path).expanduser()


CLI_POLICY = ProductCliPolicy(
    program="fmfsolver-cli",
    description="Run FMF solver from CSV/Excel input without GUI.",
    runtime_policy=RUNTIME_POLICY,
    read_cases=read_cases,
    validate_output_path=_validate_output,
    reject_input_collision_with_parser=True,
)


def build_parser():
    return build_product_parser(CLI_POLICY)


def main(argv: list[str] | None = None) -> int:
    return run_cli(CLI_POLICY, argv)


__all__ = ("build_parser", "main")
