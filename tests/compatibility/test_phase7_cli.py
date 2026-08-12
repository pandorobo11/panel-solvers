from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fmfsolver.app.cli_app import CLI_POLICY as FMF_CLI_POLICY
from fmfsolver.app.cli_app import build_parser as build_fmf_parser
from fmfsolver.app.cli_app import main as fmf_main
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from newtsolver.app.cli_app import CLI_POLICY as NEWT_CLI_POLICY
from newtsolver.app.cli_app import build_parser as build_newt_parser
from panelsolver.app.cli import parse_case_ids

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"
GOLDEN = Path(__file__).parents[1] / "fixtures" / "phase1" / "golden"


class Phase7CliTests(unittest.TestCase):
    def test_exact_frozen_help_and_d008_cardinality(self) -> None:
        with patch.dict(os.environ, {"COLUMNS": "80"}):
            for product, builder in (
                ("fmfsolver", build_fmf_parser),
                ("newtsolver", build_newt_parser),
            ):
                with self.subTest(product=product):
                    expected = json.loads(
                        (GOLDEN / product / "contracts.json").read_text(
                            encoding="utf-8"
                        )
                    )["cli"]["help"]
                    self.assertEqual(expected, builder().format_help())

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as fmf_exit:
                build_fmf_parser().parse_args(["--input", "cases.csv", "--cases"])
        self.assertEqual(2, fmf_exit.exception.code)
        newt = build_newt_parser().parse_args(
            ["--input", "cases.csv", "--cases"]
        )
        self.assertEqual([], newt.cases)

    def test_case_selector_keeps_comma_space_and_empty_contract(self) -> None:
        self.assertEqual({"a", "b", "c"}, parse_case_ids(["a,b", " c "]))
        self.assertIsNone(parse_case_ids(None))
        self.assertIsNone(parse_case_ids([]))
        self.assertIsNone(parse_case_ids([" , "]))

    def test_argument_errors_and_unknown_cases_keep_exit_boundaries(self) -> None:
        for policy in (FMF_CLI_POLICY, NEWT_CLI_POLICY):
            with self.subTest(product=policy.runtime_policy.product_id):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as workers_exit:
                        parser = (
                            build_fmf_parser()
                            if policy is FMF_CLI_POLICY
                            else build_newt_parser()
                        )
                        args = parser.parse_args(["--input", "x", "--workers", "0"])
                        if args.workers < 1:
                            parser.error("--workers must be >= 1")
                self.assertEqual(2, workers_exit.exception.code)

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "cases.csv"
            frame = read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[[0]].copy()
            frame.to_csv(input_path, index=False)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as collision_exit:
                    fmf_main(
                        [
                            "--input",
                            str(input_path),
                            "--output",
                            str(input_path),
                            "--flush-every-cases",
                            "0",
                        ]
                    )
            self.assertEqual(2, collision_exit.exception.code)
            with self.assertRaisesRegex(ValueError, "Unknown case_id"):
                fmf_main(
                    [
                        "--input",
                        str(input_path),
                        "--cases",
                        "missing",
                        "--flush-every-cases",
                        "0",
                    ]
                )

    def test_selected_cases_retain_input_order_not_option_order(self) -> None:
        frame = read_fmf_cases(INPUTS / "fmfsolver_cases.csv").iloc[[0, 1]].copy()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frame["out_dir"] = str(root / "artifacts")
            frame["save_vtp_on"] = 0
            frame["save_npz_on"] = 0
            input_path = root / "cases.csv"
            output = root / "results.csv"
            frame.to_csv(input_path, index=False)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    0,
                    fmf_main(
                        [
                            "--input",
                            str(input_path),
                            "--output",
                            str(output),
                            "--cases",
                            "fmf_mode_b_offset,fmf_zero_plate",
                            "--flush-every-cases",
                            "0",
                        ]
                    ),
                )
            result = read_fmf_cases(input_path)
            self.assertEqual(
                ["fmf_zero_plate", "fmf_mode_b_offset"],
                result["case_id"].tolist(),
            )
            import pandas as pd

            summary = pd.read_csv(output)
            self.assertEqual(
                ["fmf_zero_plate", "fmf_mode_b_offset"],
                summary.loc[summary["scope"] == "total", "case_id"].tolist(),
            )


if __name__ == "__main__":
    unittest.main()
