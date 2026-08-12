#!/usr/bin/env python3
"""Smoke the frozen command surface from an installed wheel outside the repo."""

from __future__ import annotations

import csv
import importlib.metadata
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_ENTRY_POINTS = {
    "fmfsolver": "fmfsolver.app.gui_app:main",
    "fmfsolver-gui": "fmfsolver.app.gui_app:main",
    "fmfsolver-cli": "fmfsolver.app.cli_app:main",
    "newtsolver": "newtsolver.app.gui_app:main",
    "newtsolver-gui": "newtsolver.app.gui_app:main",
    "newtsolver-cli": "newtsolver.app.cli_app:main",
}


def _command_path(name: str) -> Path:
    scripts = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    return scripts / f"{name}{suffix}"


def main() -> int:
    repository = Path(sys.argv[1]).resolve()
    contracts = repository / "tests" / "fixtures" / "phase1" / "golden"
    installed = {
        entry.name: entry.value
        for entry in importlib.metadata.distribution("panel-solvers").entry_points
        if entry.group == "console_scripts"
    }
    if installed != EXPECTED_ENTRY_POINTS:
        raise RuntimeError(f"Unexpected console scripts: {installed}")

    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(temp_dir)
        inputs = staging / "inputs"
        shutil.copytree(
            repository / "tests" / "fixtures" / "phase1" / "inputs",
            inputs,
        )
        for product in ("fmfsolver", "newtsolver"):
            command = _command_path(f"{product}-cli")
            help_result = subprocess.run(
                [command, "--help"],
                cwd=staging,
                capture_output=True,
                text=True,
                check=False,
            )
            expected_help = json.loads(
                (contracts / product / "contracts.json").read_text(encoding="utf-8")
            )["cli"]["help"]
            if help_result.returncode != 0 or help_result.stdout != expected_help:
                raise RuntimeError(
                    f"{product} help mismatch: {help_result.returncode}\n"
                    f"stdout={help_result.stdout!r}\nstderr={help_result.stderr!r}"
                )

            output = staging / f"{product}_results.csv"
            run_result = subprocess.run(
                [
                    command,
                    "--input",
                    inputs / f"{product}_cases.csv",
                    "--output",
                    output,
                    "--workers",
                    "1",
                    "--flush-every-cases",
                    "0",
                ],
                cwd=staging,
                capture_output=True,
                text=True,
                check=False,
            )
            if run_result.returncode != 0:
                raise RuntimeError(
                    f"{product} sample failed:\n{run_result.stdout}\n{run_result.stderr}"
                )
            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                columns = list(reader.fieldnames or ())
            contract = json.loads(
                (contracts / product / "contracts.json").read_text(encoding="utf-8")
            )["cli_run"]
            if columns != contract["result_csv_columns"]:
                raise RuntimeError(f"{product} result columns changed")
            case_order = [row["case_id"] for row in rows if row["scope"] == "total"]
            if case_order != contract["case_order"]:
                raise RuntimeError(f"{product} case order changed: {case_order}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
