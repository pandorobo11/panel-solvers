from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from panelsolver.app.path_resolution import (
    default_summary_output_path,
    resolve_case_output_dir,
    resolve_case_vtp_path,
    resolve_input_relative_path,
)


class PathResolutionTests(unittest.TestCase):
    def test_relative_artifacts_share_the_input_table_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "project" / "input.csv"
            row = {"case_id": "case001", "out_dir": "outputs"}
            self.assertEqual(
                input_path.parent / "outputs",
                resolve_case_output_dir(row, input_path),
            )
            self.assertEqual(
                input_path.parent / "outputs" / "case001.vtp",
                resolve_case_vtp_path(row, input_path),
            )
            self.assertEqual(
                input_path.parent / "outputs" / "input_result.csv",
                default_summary_output_path(input_path),
            )

    def test_absolute_output_directory_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            absolute = root / "shared-artifacts"
            input_path = root / "project" / "input.csv"
            self.assertEqual(
                absolute,
                resolve_input_relative_path(absolute, input_path),
            )
            self.assertEqual(
                absolute,
                resolve_case_output_dir(
                    {"case_id": "one", "out_dir": str(absolute)},
                    input_path,
                ),
            )


if __name__ == "__main__":
    unittest.main()
