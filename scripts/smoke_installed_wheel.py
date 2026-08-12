#!/usr/bin/env python3
"""Smoke the frozen command surface from an installed wheel outside the repo."""

from __future__ import annotations

import csv
import importlib
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

EXPECTED_PANEL_CORE_ALL = [
    "ATTITUDE_INPUT_VALUES",
    "WINDWARD_EQUATION_VALUES",
    "LEEWARD_EQUATION_VALUES",
    "_resolve_attitude_mode",
    "normalize_windward_equation",
    "normalize_leeward_equation",
    "modified_newtonian_cp_max",
    "_oblique_theta_from_beta",
    "_tangent_wedge_detach_limit",
    "_weak_oblique_shock_beta",
    "tangent_wedge_pressure_coefficient",
    "_tangent_cone_detach_limit",
    "tangent_cone_pressure_coefficient",
    "_prandtl_meyer_nu",
    "_inverse_prandtl_meyer",
    "resolve_attitude_to_vhat",
    "panel_force_density",
    "stl_to_body",
    "rot_y",
]
EXPECTED_PRESSURE_MODELS_ALL = [
    "modified_newtonian_cp_max",
    "_prandtl_meyer_nu",
    "_inverse_prandtl_meyer",
    "prandtl_meyer_pressure_coefficient",
    "_oblique_theta_from_beta",
    "_tangent_wedge_detach_limit",
    "_weak_oblique_shock_beta",
    "tangent_wedge_pressure_coefficient",
    "_tangent_cone_detach_limit",
    "tangent_cone_pressure_coefficient",
]


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

    contract_data = {
        product: json.loads(
            (contracts / product / "contracts.json").read_text(encoding="utf-8")
        )
        for product in ("fmfsolver", "newtsolver")
    }
    for product, version in (("fmfsolver", "1.3.8"), ("newtsolver", "1.0.3")):
        package = importlib.import_module(product)
        if package.__all__ != []:
            raise RuntimeError(f"{product} root __all__ changed: {package.__all__!r}")
        if package.__version__ != version:
            raise RuntimeError(f"{product} compatibility version changed")
        for module_name in contract_data[product]["module_paths"]:
            importlib.import_module(module_name)

    panel_core = importlib.import_module("newtsolver.core.panel_core")
    pressure_models = importlib.import_module("newtsolver.core.pressure_models")
    if panel_core.__all__ != EXPECTED_PANEL_CORE_ALL:
        raise RuntimeError("newtsolver.core.panel_core.__all__ changed")
    if pressure_models.__all__ != EXPECTED_PRESSURE_MODELS_ALL:
        raise RuntimeError("newtsolver.core.pressure_models.__all__ changed")

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
            expected_help = contract_data[product]["cli"]["help"]
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
            contract = contract_data[product]["cli_run"]
            if columns != contract["result_csv_columns"]:
                raise RuntimeError(f"{product} result columns changed")
            case_order = [row["case_id"] for row in rows if row["scope"] == "total"]
            if case_order != contract["case_order"]:
                raise RuntimeError(f"{product} case order changed: {case_order}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
