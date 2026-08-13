#!/usr/bin/env python3
"""Smoke the frozen command surface from an installed wheel outside the repo."""

from __future__ import annotations

import csv
import importlib
import importlib.metadata
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv

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
EXPECTED_EXPORTER_SIGNATURES = {
    "export_vtp": (
        "(out_path: 'str', vertices: 'np.ndarray', faces: 'np.ndarray', "
        "cell_data: 'dict', field_data: 'dict | None' = None)"
    ),
    "export_npz": "(out_path: 'str', **arrays)",
}
EXPECTED_DIRECT_COMPONENT_KEYS = [
    "scope",
    "component_id",
    "component_stl_path",
    "CA",
    "CY",
    "CN",
    "Cl",
    "Cm",
    "Cn",
    "CD",
    "CL",
    "faces",
    "shielded_faces",
    "vtp_path",
    "npz_path",
]
MESH_WARNING = "[WARN] Mesh is not watertight (trimesh). Continuing anyway."
EXPECTED_CLI_DESCRIPTIONS = {
    "fmfsolver": "Run FMF solver from CSV/Excel input without GUI.",
    "newtsolver": "Run newtsolver from CSV/Excel input without GUI.",
}


def _expected_backend_hint(product: str, *, embree: bool) -> str:
    if embree:
        return "[INFO] Ray backend: Embree (ray_pyembree)."
    return (
        "[INFO] Ray backend: rtree (ray_triangle). Optional acceleration is "
        "available: uv sync --extra rayaccel (or pip install "
        f'"{product}[rayaccel]").'
    )


def _command_path(name: str) -> Path:
    scripts = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    return scripts / f"{name}{suffix}"


def _validate_cli_help(product: str, help_text: str) -> None:
    required = (
        f"usage: {product}-cli",
        EXPECTED_CLI_DESCRIPTIONS[product],
        "--input INPUT",
        "--output OUTPUT",
        "--workers WORKERS",
        "--cases CASES [CASES ...]",
        "--flush-every-cases FLUSH_EVERY_CASES",
    )
    missing = [fragment for fragment in required if fragment not in help_text]
    if missing:
        raise RuntimeError(f"{product} help is missing Phase 8 contract: {missing}")


def _smoke_direct_exporters(staging: Path) -> None:
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=np.float32,
    )
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    cell_data = {"Cp_n": np.array([1.25], dtype=np.float32)}
    field_data = {"case_id": "installed-direct"}
    npz_arrays = {
        "panel_id": np.array([7], dtype=np.int16),
        "loads": np.array([[1.25, -0.5, 0.0]], dtype=np.float32),
    }

    for product in ("fmfsolver", "newtsolver"):
        module_name = f"{product}.io.exporters"
        module = importlib.import_module(module_name)
        for name, expected_signature in EXPECTED_EXPORTER_SIGNATURES.items():
            function = getattr(module, name)
            if str(inspect.signature(function)) != expected_signature:
                raise RuntimeError(f"{module_name}.{name} signature changed")
            if function.__name__ != name or function.__module__ != module_name:
                raise RuntimeError(f"{module_name}.{name} identity changed")

        output = staging / "direct-exporters" / product
        vtp_path = output / "direct.vtp"
        result = module.export_vtp(
            out_path=vtp_path,
            vertices=vertices,
            faces=faces,
            cell_data=cell_data,
            field_data=field_data,
        )
        if result is not None:
            raise RuntimeError(f"{module_name}.export_vtp must return None")
        poly = pv.read(vtp_path)
        if list(poly.cell_data) != list(cell_data):
            raise RuntimeError(f"{module_name}.export_vtp cell names changed")
        if list(poly.field_data) != list(field_data):
            raise RuntimeError(f"{module_name}.export_vtp metadata names changed")
        if not np.array_equal(poly.cell_data["Cp_n"], cell_data["Cp_n"]):
            raise RuntimeError(f"{module_name}.export_vtp cell values changed")
        if poly.cell_data["Cp_n"].dtype != cell_data["Cp_n"].dtype:
            raise RuntimeError(f"{module_name}.export_vtp cell dtype changed")
        expected_case_id = np.asarray([field_data["case_id"]])
        if not np.array_equal(poly.field_data["case_id"], expected_case_id):
            raise RuntimeError(f"{module_name}.export_vtp metadata changed")

        npz_path = output / "direct.npz"
        result = module.export_npz(out_path=npz_path, **npz_arrays)
        if result is not None:
            raise RuntimeError(f"{module_name}.export_npz must return None")
        with np.load(npz_path) as archive:
            if archive.files != list(npz_arrays):
                raise RuntimeError(f"{module_name}.export_npz names changed")
            for name, expected in npz_arrays.items():
                if not np.array_equal(archive[name], expected):
                    raise RuntimeError(f"{module_name}.export_npz {name} changed")
                if archive[name].dtype != expected.dtype:
                    raise RuntimeError(f"{module_name}.export_npz {name} dtype changed")


def _smoke_direct_solver_results(staging: Path, inputs: Path) -> None:
    products = (
        ("fmfsolver", "fmfsolver_cases.csv", 3),
        ("newtsolver", "newtsolver_cases.csv", 6),
    )
    runtime = importlib.import_module("panelsolver.app.runtime")
    for product, filename, multi_index in products:
        reader = importlib.import_module(f"{product}.io.io_cases").read_cases
        solver = importlib.import_module(f"{product}.core.solver")
        source = reader(inputs / filename)
        row = source.iloc[multi_index].to_dict()
        output = staging / "direct-solvers" / product
        row.update(out_dir=str(output), save_vtp_on=0, save_npz_on=0)

        runtime._RAY_ACCEL_HINTED_PRODUCTS.discard(product)
        direct_logs: list[str] = []
        result = solver.run_case(row, direct_logs.append)
        if direct_logs != [MESH_WARNING]:
            raise RuntimeError(f"{product} direct-case logs changed: {direct_logs!r}")
        if product in runtime._RAY_ACCEL_HINTED_PRODUCTS:
            raise RuntimeError(f"{product} direct case consumed backend hint")

        owned = LookupError(f"{product} installed hint callback")

        def fail_hint(_message: str, error: BaseException = owned) -> None:
            raise error

        try:
            solver.run_cases(source.iloc[0:0], fail_hint)
        except BaseException as exc:
            if exc is not owned:
                raise RuntimeError(
                    f"{product} empty hint callback identity changed"
                ) from exc
        else:
            raise RuntimeError(f"{product} empty hint callback error was ignored")
        if product in runtime._RAY_ACCEL_HINTED_PRODUCTS:
            raise RuntimeError(f"{product} failed hint callback consumed state")

        empty_logs: list[str] = []
        empty = solver.run_cases(source.iloc[0:0], empty_logs.append)
        if not empty.empty or tuple(empty.shape) != (0, 0):
            raise RuntimeError(f"{product} empty direct batch result changed")
        expected_hint = _expected_backend_hint(
            product,
            embree=bool(runtime.trimesh_ray.has_embree),
        )
        if empty_logs != [expected_hint]:
            raise RuntimeError(f"{product} empty backend hint changed: {empty_logs!r}")
        if product not in runtime._RAY_ACCEL_HINTED_PRODUCTS:
            raise RuntimeError(f"{product} successful backend hint was not recorded")
        hot_logs: list[str] = []
        solver.run_cases(source.iloc[0:0], hot_logs.append)
        if hot_logs:
            raise RuntimeError(f"{product} repeated empty hint: {hot_logs!r}")

        components = result["component_rows"]
        expected_sources = row["stl_path"].split(";")
        if any(list(item) != EXPECTED_DIRECT_COMPONENT_KEYS for item in components):
            raise RuntimeError(f"{product} component row schema changed")
        expected_types = (
            str,
            int,
            str,
            float,
            float,
            float,
            float,
            float,
            float,
            float,
            float,
            int,
            int,
            str,
            str,
        )
        if any(
            tuple(type(value) for value in item.values()) != expected_types
            for item in components
        ):
            raise RuntimeError(f"{product} component row value types changed")
        if result["component_id"] != "" or type(result["component_id"]) is not str:
            raise RuntimeError(f"{product} total component_id type/blank changed")
        if (
            result["component_stl_path"] != ""
            or type(result["component_stl_path"]) is not str
        ):
            raise RuntimeError(f"{product} total component_stl_path changed")
        if result["vtp_path"] != "" or result["npz_path"] != "":
            raise RuntimeError(f"{product} disabled total artifact paths changed")
        if [item["component_id"] for item in components] != [0, 1] or not all(
            type(item["component_id"]) is int for item in components
        ):
            raise RuntimeError(f"{product} component IDs changed")
        if [item["component_stl_path"] for item in components] != expected_sources:
            raise RuntimeError(f"{product} component STL order changed")
        if any(item["vtp_path"] != "" for item in components) or any(
            item["npz_path"] != "" for item in components
        ):
            raise RuntimeError(f"{product} component artifact paths changed")


def _smoke_direct_solver_errors(staging: Path, inputs: Path) -> None:
    products = (
        ("fmfsolver", "fmfsolver_cases.csv"),
        ("newtsolver", "newtsolver_cases.csv"),
    )
    for product, filename in products:
        reader = importlib.import_module(f"{product}.io.io_cases").read_cases
        solver = importlib.import_module(f"{product}.core.solver")
        source = reader(inputs / filename)
        cancel_calls = 0

        def cancel() -> bool:
            nonlocal cancel_calls
            cancel_calls += 1
            return True

        try:
            solver.run_cases(
                source.iloc[0:0],
                lambda _message: None,
                cancel_cb=cancel,
            )
        except BaseException as exc:
            if (
                type(exc) is not RuntimeError
                or str(exc) != "Canceled by user."
                or exc.__cause__ is not None
                or exc.__context__ is not None
            ):
                raise RuntimeError(f"{product} empty cancellation changed") from exc
        else:
            raise RuntimeError(f"{product} empty cancellation was ignored")
        if cancel_calls != 1:
            raise RuntimeError(f"{product} empty cancellation callback count changed")

        missing = staging / "direct-errors" / product / "missing.stl"
        try:
            missing.resolve().open("rb")
        except FileNotFoundError as exc:
            expected_missing_message = str(exc)
        else:
            raise RuntimeError("installed-wheel missing-STL fixture exists")
        row = source.iloc[0].to_dict()
        row.update(
            stl_path=str(missing),
            out_dir=str(staging / "direct-errors" / product / "serial"),
            save_vtp_on=1,
            save_npz_on=1,
        )
        try:
            solver.run_case(row, lambda _message: None)
        except BaseException as exc:
            if (
                type(exc) is not FileNotFoundError
                or str(exc) != expected_missing_message
                or exc.__cause__ is not None
                or exc.__context__ is not None
            ):
                raise RuntimeError(f"{product} serial missing-STL error changed") from exc
        else:
            raise RuntimeError(f"{product} serial missing STL succeeded")

        parallel = source.iloc[[0, 0]].copy().reset_index(drop=True)
        parallel["case_id"] = [f"{product}-missing-0", f"{product}-missing-1"]
        parallel["stl_path"] = str(missing)
        parallel["out_dir"] = [
            str(staging / "direct-errors" / product / "parallel-0"),
            str(staging / "direct-errors" / product / "parallel-1"),
        ]
        parallel["save_vtp_on"] = 1
        parallel["save_npz_on"] = 1
        try:
            solver.run_cases(parallel, lambda _message: None, workers=2)
        except BaseException as exc:
            expected_first_line = f"[WorkerError] {expected_missing_message}"
            if (
                type(exc) is not RuntimeError
                or str(exc).splitlines()[0] != expected_first_line
                or "FileNotFoundError:" not in str(exc)
                or exc.__cause__ is not None
                or exc.__context__ is not None
            ):
                raise RuntimeError(
                    f"{product} parallel missing-STL error changed"
                ) from exc
        else:
            raise RuntimeError(f"{product} parallel missing STL succeeded")


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
        _smoke_direct_exporters(staging)
        inputs = staging / "inputs"
        shutil.copytree(
            repository / "tests" / "fixtures" / "phase1" / "inputs",
            inputs,
        )
        _smoke_direct_solver_results(staging, inputs)
        _smoke_direct_solver_errors(staging, inputs)
        for product in ("fmfsolver", "newtsolver"):
            command = _command_path(f"{product}-cli")
            help_result = subprocess.run(
                [command, "--help"],
                cwd=staging,
                capture_output=True,
                text=True,
                check=False,
            )
            if help_result.returncode != 0:
                raise RuntimeError(
                    f"{product} help failed: {help_result.returncode}\n"
                    f"stdout={help_result.stdout!r}\nstderr={help_result.stderr!r}"
                )
            _validate_cli_help(product, help_result.stdout)

            empty_cases = subprocess.run(
                [command, "--input", "cases.csv", "--cases"],
                cwd=staging,
                capture_output=True,
                text=True,
                check=False,
            )
            if empty_cases.returncode != 2 or "expected at least one argument" not in (
                empty_cases.stderr
            ):
                raise RuntimeError(
                    f"{product} explicit empty --cases did not fail in argparse: "
                    f"{empty_cases.returncode}\nstdout={empty_cases.stdout!r}\n"
                    f"stderr={empty_cases.stderr!r}"
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
