from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np

from fmfsolver import legacy_adapter as fmf_adapter
from newtsolver import legacy_adapter as newt_adapter
from panelsolver.app import LegacyPanelSnapshot, LegacyRunContext
from panelsolver.core import CommonCasePayload, ModelCasePayload

REPOSITORY_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "phase1"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"
MANIFEST = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
GEOMETRY_CELL_FIELDS = {
    "C_face_stl",
    "area_m2",
    "center_x_stl_m",
    "center_y_stl_m",
    "center_z_stl_m",
    "shielded",
    "stl_index",
}


def _record_array(record: dict) -> np.ndarray:
    return np.asarray(record["values"]).reshape(record["shape"])


def _npz_array(golden: dict, name: str) -> np.ndarray:
    return _record_array(golden["npz"]["arrays"][name])


def _scalar(record: dict) -> object:
    return _record_array(record).item()


def _array_record(value: np.ndarray) -> dict:
    array = np.asarray(value)
    logical_dtype = {
        "b": "bool",
        "i": f"int{array.dtype.itemsize * 8}",
        "u": f"uint{array.dtype.itemsize * 8}",
        "f": f"float{array.dtype.itemsize * 8}",
        "U": "string",
        "S": "string",
    }[array.dtype.kind]
    return {
        "dtype": logical_dtype,
        "shape": list(array.shape),
        "values": array.tolist(),
    }


def _semantic_projection(bundle) -> dict:
    return {
        "csv": {
            "columns": list(bundle.csv.columns),
            "rows": [dict(row) for row in bundle.csv.rows],
        },
        "vtp": {
            "points": _array_record(bundle.vtp.points),
            "faces": _array_record(bundle.vtp.faces),
            "cell_data": {
                name: _array_record(array)
                for name, array in bundle.vtp.cell_data.items()
            },
            "field_data": {
                name: _array_record(array)
                for name, array in bundle.vtp.field_data.items()
            },
        },
        "npz": {
            "arrays": {
                name: _array_record(array)
                for name, array in bundle.npz.arrays.items()
            }
        },
    }


def _load_comparator_module():
    script = REPOSITORY_ROOT / "scripts" / "generate_phase1_goldens.py"
    spec = importlib.util.spec_from_file_location("phase3_adapter_comparator", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the Phase 1 semantic comparator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Phase3LegacyAdapterGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.comparator = _load_comparator_module()

    def test_complete_semantic_matrix_through_product_adapters(self) -> None:
        paths = sorted(GOLDEN_ROOT.glob("*/*.json"))
        paths = [path for path in paths if path.name != "contracts.json"]
        self.assertEqual(15, len(paths))

        for path in paths:
            with self.subTest(solver=path.parent.name, case_id=path.stem):
                golden = json.loads(path.read_text(encoding="utf-8"))
                normalized = golden["normalized_input"]
                field_data = golden["vtp"]["field_data"]
                npz_records = golden["npz"]["arrays"]
                total_row = golden["csv"]["rows"][0]
                areas = _npz_array(golden, "areas_m2")
                face_force = _record_array(
                    golden["vtp"]["cell_data"]["C_face_stl"]
                )
                snapshot = LegacyPanelSnapshot(
                    vertices_stl_m=_npz_array(golden, "vertices"),
                    faces=_npz_array(golden, "faces").astype(np.int64),
                    centers_stl_m=_npz_array(golden, "centers_stl_m"),
                    normals_out_stl=_npz_array(golden, "normals_out_stl"),
                    areas_m2=areas,
                    component_ids=_npz_array(golden, "face_stl_index").astype(np.int64),
                    component_sources=tuple(
                        str(source)
                        for source in _npz_array(golden, "stl_paths").tolist()
                    ),
                    shielded=_npz_array(golden, "shielded").astype(bool),
                    traction_coeff_stl=(
                        face_force * (normalized["Aref_m2"] / areas)[:, None]
                    ),
                    cell_scalars={
                        name: _record_array(record)
                        for name, record in golden["vtp"]["cell_data"].items()
                        if name not in GEOMETRY_CELL_FIELDS
                    },
                )
                case = CommonCasePayload(
                    case_id=normalized["case_id"],
                    Aref_m2=normalized["Aref_m2"],
                    moment_reference_stl_m=[
                        normalized["ref_x_m"],
                        normalized["ref_y_m"],
                        normalized["ref_z_m"],
                    ],
                    Lref_Cl_m=normalized["Lref_Cl_m"],
                    Lref_Cm_m=normalized["Lref_Cm_m"],
                    Lref_Cn_m=normalized["Lref_Cn_m"],
                    alpha_t_deg=float(_npz_array(golden, "alpha_t_deg_resolved")),
                    beta_t_deg=float(_npz_array(golden, "beta_t_deg_resolved")),
                )
                run = LegacyRunContext(
                    attitude_input_used=str(_scalar(field_data["attitude_input_used"])),
                    case_signature=str(_scalar(field_data["case_signature"])),
                    ray_backend_used=str(_scalar(field_data["ray_backend_used"])),
                    solver_version=str(_scalar(field_data["solver_version"])),
                    run_started_at_utc=total_row["run_started_at_utc"],
                    run_finished_at_utc=total_row["run_finished_at_utc"],
                    run_elapsed_s=total_row["run_elapsed_s"],
                    vtp_path=total_row["vtp_path"],
                    npz_path=total_row["npz_path"],
                )
                common_arguments = {
                    "case": case,
                    "model_case": ModelCasePayload(path.parent.name, normalized),
                    "snapshot": snapshot,
                    "input_row": normalized,
                    "run": run,
                }
                if path.parent.name == "fmfsolver":
                    bundle = fmf_adapter.project_case(
                        **common_arguments,
                        mode=total_row["mode"],
                        speed_ratio=total_row["out_S"],
                        translational_temperature_k=total_row["out_Ti_K"],
                        wall_temperature_k=_scalar(npz_records["Tw_K"]),
                    )
                else:
                    bundle = newt_adapter.project_case(
                        **common_arguments,
                        windward_equation_used=str(
                            _scalar(field_data["windward_eq_used"])
                        ),
                        leeward_equation_used=str(
                            _scalar(field_data["leeward_eq_used"])
                        ),
                    )

                expected = {
                    "csv": golden["csv"],
                    "vtp": golden["vtp"],
                    "npz": golden["npz"],
                }
                differences = self.comparator._compare_values(
                    expected,
                    _semantic_projection(bundle),
                    manifest=MANIFEST,
                    profile_name=golden["provenance"]["tolerance_profile"],
                )
                self.assertEqual([], differences)


if __name__ == "__main__":
    unittest.main()
