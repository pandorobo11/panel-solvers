from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pyvista as pv

from fmfsolver.case_adapter import build_signatures as build_fmf_signatures
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from fmfsolver.runtime import RUNTIME_POLICY as FMF_POLICY
from newtsolver.case_adapter import build_signatures as build_newt_signatures
from newtsolver.io.io_cases import read_cases as read_newt_cases
from newtsolver.runtime import RUNTIME_POLICY as NEWT_POLICY
from panelsolver.app import run_and_write_product_cases

REPOSITORY_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "phase1"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"
MANIFEST = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _load_comparator_module():
    script = REPOSITORY_ROOT / "scripts" / "generate_phase1_goldens.py"
    spec = importlib.util.spec_from_file_location("phase7_comparator", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the Phase 1 semantic comparator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Phase7RuntimeGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.comparator = _load_comparator_module()

    def test_all_cases_serialize_to_frozen_csv_vtp_and_npz_semantics(self) -> None:
        products = (
            (
                "fmfsolver",
                "fmfsolver_cases.csv",
                read_fmf_cases,
                build_fmf_signatures,
                FMF_POLICY,
                6,
            ),
            (
                "newtsolver",
                "newtsolver_cases.csv",
                read_newt_cases,
                build_newt_signatures,
                NEWT_POLICY,
                9,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            staged = Path(temp_dir) / "fixture"
            shutil.copytree(FIXTURE_ROOT / "inputs", staged)
            roots = {staged.resolve(): "<fixture-root>"}

            for product, filename, reader, signatures, policy, count in products:
                with self.subTest(product=product):
                    frame = reader(staged / filename)
                    rows = tuple(frame.to_dict(orient="records"))
                    output = staged / "outputs" / f"{product}_result.csv"
                    result = run_and_write_product_cases(
                        rows,
                        policy,
                        output,
                        workers=1,
                    )
                    self.assertEqual(count, len(result.cases))
                    actual_csv = self.comparator._read_semantic_csv(
                        output,
                        roots=roots,
                    )
                    with output.open(encoding="utf-8", newline="") as stream:
                        raw_csv_rows = list(csv.DictReader(stream))

                    for row in rows:
                        case_id = str(row["case_id"])
                        golden = json.loads(
                            (GOLDEN_ROOT / product / f"{case_id}.json").read_text(
                                encoding="utf-8"
                            )
                        )
                        actual_rows = [
                            csv_row
                            for csv_row in actual_csv["rows"]
                            if csv_row["case_id"] == case_id
                        ]
                        actual = {
                            "csv": {
                                "columns": actual_csv["columns"],
                                "rows": actual_rows,
                            },
                            "vtp": self.comparator._read_vtp(
                                staged / "outputs" / f"{case_id}.vtp",
                                roots=roots,
                            ),
                            "npz": self.comparator._read_npz(
                                staged / "outputs" / f"{case_id}.npz",
                                roots=roots,
                            ),
                        }
                        expected = {
                            name: golden[name] for name in ("csv", "vtp", "npz")
                        }
                        differences = self.comparator._compare_values(
                            expected,
                            actual,
                            manifest=MANIFEST,
                            profile_name=golden["provenance"]["tolerance_profile"],
                        )
                        self.assertEqual([], differences)

                        raw_total = next(
                            csv_row
                            for csv_row in raw_csv_rows
                            if csv_row["case_id"] == case_id
                            and csv_row["scope"] == "total"
                        )
                        poly = pv.read(staged / "outputs" / f"{case_id}.vtp")
                        primary = signatures(row).primary.digest
                        self.assertEqual(primary, raw_total["case_signature"])
                        self.assertEqual(
                            primary,
                            str(poly.field_data["case_signature"][0]),
                        )


if __name__ == "__main__":
    unittest.main()
