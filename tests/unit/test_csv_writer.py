from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fmfsolver import csv_adapter as fmf_csv
from fmfsolver.app.cli_app import CLI_POLICY as FMF_CLI_POLICY
from fmfsolver.runtime import GUI_ADAPTERS as FMF_GUI_ADAPTERS
from newtsolver import csv_adapter as newt_csv
from newtsolver.app.cli_app import CLI_POLICY as NEWT_CLI_POLICY
from newtsolver.runtime import GUI_ADAPTERS as NEWT_GUI_ADAPTERS
from panelsolver.app.csv_writer import DURABLE_CSV_WRITE_POLICY, write_csv_atomic
from panelsolver.core import CsvProjection


def projection() -> CsvProjection:
    return CsvProjection(
        ("case_id", "scope", "blank"),
        (
            {"case_id": "a", "scope": "total", "blank": None},
            {"case_id": "a", "scope": "component", "blank": None},
        ),
    )


class CsvWriterTests(unittest.TestCase):
    def test_products_use_one_durable_write_policy(self) -> None:
        self.assertIs(DURABLE_CSV_WRITE_POLICY, fmf_csv.CSV_WRITE_POLICY)
        self.assertIs(DURABLE_CSV_WRITE_POLICY, newt_csv.CSV_WRITE_POLICY)
        self.assertTrue(DURABLE_CSV_WRITE_POLICY.fsync_before_replace)

    def test_both_products_flush_fsync_replace_and_preserve_semantic_csv(self) -> None:
        for adapter in (fmf_csv, newt_csv):
            with self.subTest(adapter=adapter.__name__), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "results.csv"
                with (
                    patch("panelsolver.app.csv_writer.os.fsync") as fsync,
                    patch(
                        "panelsolver.app.csv_writer.os.replace",
                        wraps=os.replace,
                    ) as replace,
                ):
                    adapter.write_csv(output, projection())
                fsync.assert_called_once()
                replace.assert_called_once()
                with output.open(encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    self.assertEqual(
                        [
                            {"case_id": "a", "scope": "total", "blank": ""},
                            {"case_id": "a", "scope": "component", "blank": ""},
                        ],
                        list(reader),
                    )

    def test_both_policies_preserve_output_and_clean_temp_on_failure(self) -> None:
        for policy in (fmf_csv.CSV_WRITE_POLICY, newt_csv.CSV_WRITE_POLICY):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "results.csv"
                output.write_text("original\n", encoding="utf-8")
                with (
                    patch(
                        "panelsolver.app.csv_writer._write_projection",
                        side_effect=OSError("disk error"),
                    ),
                    self.assertRaisesRegex(OSError, "disk error"),
                ):
                    write_csv_atomic(output, projection(), policy)
                self.assertEqual("original\n", output.read_text(encoding="utf-8"))
                self.assertEqual([output], list(Path(td).iterdir()))

    def test_both_policies_clean_temp_on_replace_failure(self) -> None:
        for policy in (fmf_csv.CSV_WRITE_POLICY, newt_csv.CSV_WRITE_POLICY):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "results.csv"
                output.write_text("original\n", encoding="utf-8")
                with (
                    patch(
                        "panelsolver.app.csv_writer.os.replace",
                        side_effect=OSError("replace error"),
                    ),
                    self.assertRaisesRegex(OSError, "replace error"),
                ):
                    write_csv_atomic(output, projection(), policy)
                self.assertEqual("original\n", output.read_text(encoding="utf-8"))
                self.assertEqual([output], list(Path(td).iterdir()))

    def test_both_policies_clean_temp_on_fsync_failure(self) -> None:
        for policy in (fmf_csv.CSV_WRITE_POLICY, newt_csv.CSV_WRITE_POLICY):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "results.csv"
                output.write_text("original\n", encoding="utf-8")
                with (
                    patch(
                        "panelsolver.app.csv_writer.os.fsync",
                        side_effect=OSError("fsync error"),
                    ),
                    self.assertRaisesRegex(OSError, "fsync error"),
                ):
                    write_csv_atomic(output, projection(), policy)
                self.assertEqual("original\n", output.read_text(encoding="utf-8"))
                self.assertEqual([output], list(Path(td).iterdir()))

    def test_collision_scope_is_shared_and_ignores_save_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "cases.csv"
            stl_path = root / "mesh.stl"
            second_stl_path = root / "mesh-2.stl"
            out_dir = root / "outputs"
            case_rows = (
                {
                    "case_id": "case_a",
                    "stl_path": f"{stl_path};{second_stl_path}",
                    "out_dir": str(out_dir),
                    "save_vtp_on": 0,
                    "save_npz_on": 0,
                },
            )

            for adapter in (fmf_csv, newt_csv):
                for protected in (
                    input_path,
                    stl_path,
                    second_stl_path,
                    out_dir / "case_a.vtp",
                    out_dir / "case_a.npz",
                ):
                    with self.subTest(
                        adapter=adapter.__name__, protected=protected
                    ), self.assertRaisesRegex(ValueError, "protected path"):
                        adapter.validate_results_output_path(
                            protected,
                            input_path,
                            case_rows,
                        )

    def test_cli_and_gui_use_the_shared_collision_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "cases.csv"
            stl_path = root / "mesh.stl"
            artifact = root / "outputs" / "case_a.vtp"
            rows = (
                {
                    "case_id": "case_a",
                    "stl_path": str(stl_path),
                    "out_dir": str(root / "outputs"),
                    "save_vtp_on": 0,
                    "save_npz_on": 0,
                },
            )
            validators = (
                FMF_CLI_POLICY.validate_output_path,
                NEWT_CLI_POLICY.validate_output_path,
                FMF_GUI_ADAPTERS.validate_output_path,
                NEWT_GUI_ADAPTERS.validate_output_path,
            )
            for validator in validators:
                for protected in (input_path, stl_path, artifact):
                    with self.subTest(
                        validator=validator, protected=protected
                    ), self.assertRaisesRegex(ValueError, "protected path"):
                        validator(protected, input_path, rows)


if __name__ == "__main__":
    unittest.main()
