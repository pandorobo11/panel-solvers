from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fmfsolver import csv_adapter as fmf_csv
from newtsolver import csv_adapter as newt_csv
from panelsolver.app.csv_writer import TempNameStyle, write_csv_atomic
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
    def test_product_write_policies_are_explicit(self) -> None:
        self.assertIs(
            TempNameStyle.NAMED_RANDOM,
            fmf_csv.CSV_WRITE_POLICY.temp_name_style,
        )
        self.assertTrue(fmf_csv.CSV_WRITE_POLICY.fsync_before_replace)
        self.assertIs(TempNameStyle.UUID, newt_csv.CSV_WRITE_POLICY.temp_name_style)
        self.assertFalse(newt_csv.CSV_WRITE_POLICY.fsync_before_replace)

    def test_policies_preserve_fsync_difference_and_semantic_csv(self) -> None:
        for adapter, expect_fsync in ((fmf_csv, True), (newt_csv, False)):
            with self.subTest(adapter=adapter.__name__), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "results.csv"
                with patch("panelsolver.app.csv_writer.os.fsync") as fsync:
                    adapter.write_csv(output, projection())
                self.assertEqual(expect_fsync, fsync.called)
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

    def test_collision_scopes_remain_product_specific(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "cases.csv"
            stl_path = root / "mesh.stl"
            out_dir = root / "outputs"
            case_rows = (
                {
                    "case_id": "case_a",
                    "stl_path": str(stl_path),
                    "out_dir": str(out_dir),
                    "save_vtp_on": 0,
                    "save_npz_on": 0,
                },
            )

            with self.assertRaisesRegex(ValueError, "protected path"):
                fmf_csv.validate_results_output_path(input_path, input_path)
            self.assertEqual(
                stl_path.resolve(),
                fmf_csv.validate_results_output_path(stl_path, input_path),
            )
            for protected in (
                input_path,
                stl_path,
                out_dir / "case_a.vtp",
                out_dir / "case_a.npz",
            ):
                with self.subTest(protected=protected), self.assertRaisesRegex(
                    ValueError,
                    "protected path",
                ):
                    newt_csv.validate_results_output_path(
                        protected,
                        input_path,
                        case_rows,
                    )


if __name__ == "__main__":
    unittest.main()
