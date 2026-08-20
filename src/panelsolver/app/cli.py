"""Shared batch-command orchestration with product-selected parser policy."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .runtime import (
    DEFAULT_CHECKPOINT_CASES,
    ProductRuntimePolicy,
    run_and_write_product_cases,
)

type ReadCasesCallback = Callable[[str | Path], pd.DataFrame]
type ValidateOutputCallback = Callable[
    [str | Path, str | Path, Sequence[Mapping[str, object]]], Path
]


@dataclass(frozen=True, slots=True)
class ProductCliPolicy:
    """Exact parser text and product callbacks for one legacy command."""

    program: str
    description: str
    runtime_policy: ProductRuntimePolicy
    read_cases: ReadCasesCallback
    validate_output_path: ValidateOutputCallback

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_policy, ProductRuntimePolicy):
            raise TypeError("runtime_policy must be a ProductRuntimePolicy")
        for name in ("program", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        for name in ("read_cases", "validate_output_path"):
            if not callable(getattr(self, name)):
                raise TypeError(f"{name} must be callable")


def parse_case_ids(values: list[str] | None) -> set[str] | None:
    """Parse the frozen comma/space-separated case selector."""
    if not values:
        return None
    case_ids: set[str] = set()
    for value in values:
        for token in value.split(","):
            normalized = token.strip()
            if normalized:
                case_ids.add(normalized)
    return case_ids or None


def build_parser(policy: ProductCliPolicy) -> argparse.ArgumentParser:
    """Create one parser with product text and the shared selection contract."""
    if not isinstance(policy, ProductCliPolicy):
        raise TypeError("policy must be a ProductCliPolicy")
    parser = argparse.ArgumentParser(
        prog=policy.program,
        description=policy.description,
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input cases file (.csv/.xlsx/.xlsm)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output result CSV path "
            "(default: <input_dir>/outputs/<input_stem>_result.csv)"
        ),
    )
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1)",
    )
    parser.add_argument(
        "--cases",
        nargs="+",
        default=None,
        help="Run only selected case_id values (space/comma separated).",
    )
    parser.add_argument(
        "--checkpoint-every-cases",
        type=int,
        default=DEFAULT_CHECKPOINT_CASES,
        help=(
            "Checkpoint output every N completed cases "
            f"(0 to disable, default: {DEFAULT_CHECKPOINT_CASES})."
        ),
    )
    return parser


def run_cli(policy: ProductCliPolicy, argv: list[str] | None = None) -> int:
    """Read, select, run, checkpoint, and write one product CLI request."""
    parser = build_parser(policy)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.checkpoint_every_cases < 0:
        parser.error("--checkpoint-every-cases must be >= 0")

    input_path = Path(args.input).expanduser()
    frame = policy.read_cases(input_path)
    if len(frame) == 0:
        raise ValueError("Input file has no cases.")

    case_ids = parse_case_ids(args.cases)
    if case_ids is not None:
        selected = frame[
            frame["case_id"].astype(str).isin(case_ids)
        ].reset_index(drop=True)
        missing = sorted(case_ids - set(frame["case_id"].astype(str)))
        if missing:
            raise ValueError(f"Unknown case_id values: {missing}")
        if len(selected) == 0:
            raise ValueError("No cases selected.")
        run_frame = selected
    else:
        run_frame = frame.reset_index(drop=True)
    rows = tuple(run_frame.to_dict(orient="records"))

    raw_output = (
        Path(args.output).expanduser()
        if args.output
        else input_path.parent / "outputs" / f"{input_path.stem}_result.csv"
    )
    output = policy.validate_output_path(raw_output, input_path, rows)
    output.parent.mkdir(parents=True, exist_ok=True)

    def logfn(message: str) -> None:
        print(message, flush=True)

    print(
        f"[RUN] cases={len(rows)} workers={args.workers} input={input_path}",
        flush=True,
    )
    run_and_write_product_cases(
        rows,
        policy.runtime_policy,
        output,
        workers=args.workers,
        logfn=logfn,
        checkpoint_every_cases=args.checkpoint_every_cases,
        log_snapshots=args.checkpoint_every_cases > 0,
    )
    print(f"[OK] Wrote results: {output}", flush=True)
    return 0


__all__ = ("ProductCliPolicy", "build_parser", "parse_case_ids", "run_cli")
