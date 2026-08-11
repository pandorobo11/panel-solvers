#!/usr/bin/env python3
"""Compare two Phase 1 capture trees using manifest quantity tolerances."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_phase1_goldens import compare_capture_trees


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "phase1"
        / "manifest.json",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    differences = compare_capture_trees(
        args.expected.resolve(), args.actual.resolve(), manifest
    )
    if differences:
        for difference in differences:
            print(difference)
        return 1
    print("Phase 1 semantic captures match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
