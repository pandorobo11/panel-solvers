from __future__ import annotations

import contextlib
import io
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
from newtsolver.app.cli_app import main as newt_main
from newtsolver.io.io_cases import read_cases as read_newt_cases
from panelsolver.app.cli import parse_case_ids
from tests.current_case_fixtures import read_current_cases

INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"


class Phase7CliTests(unittest.TestCase):
    def test_help_and_explicit_empty_cases_use_common_cardinality(self) -> None:
        with patch.dict(os.environ, {"COLUMNS": "80"}):
            for program, description, builder in (
                (
                    "fmfsolver-cli",
                    "Run FMF solver from CSV/Excel input without GUI.",
                    build_fmf_parser,
                ),
                (
                    "newtsolver-cli",
                    "Run newtsolver from CSV/Excel input without GUI.",
                    build_newt_parser,
                ),
            ):
                with self.subTest(program=program):
                    help_text = builder().format_help()
                    self.assertIn(f"usage: {program}", help_text)
                    self.assertIn(description, help_text)
                    self.assertIn("--cases CASES [CASES ...]", help_text)
                    self.assertIn("--flush-every-cases", help_text)
                    with contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as caught:
                            builder().parse_args(
                                ["--input", "cases.csv", "--cases"]
                            )
                    self.assertEqual(2, caught.exception.code)

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
            frame = read_current_cases(
                read_fmf_cases, INPUTS / "fmfsolver_cases.csv"
            ).iloc[[0]].copy()
            frame.to_csv(input_path, index=False)
            with self.assertRaisesRegex(ValueError, "protected path"):
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
        products = (
            (
                fmf_main,
                read_fmf_cases,
                "fmfsolver_cases.csv",
                ("fmf_zero_plate", "fmf_mode_b_offset"),
            ),
            (
                newt_main,
                read_newt_cases,
                "newtsolver_cases.csv",
                ("newt_zero_newtonian", "newt_modified_offset"),
            ),
        )
        for main, reader, filename, case_ids in products:
            frame = read_current_cases(reader, INPUTS / filename).iloc[[0, 1]].copy()
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                frame["out_dir"] = str(root / "artifacts")
                frame["save_vtp_on"] = 0
                input_path = root / "cases.csv"
                output = root / "results.csv"
                frame.to_csv(input_path, index=False)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        0,
                        main(
                            [
                                "--input",
                                str(input_path),
                                "--output",
                                str(output),
                                "--cases",
                                f"{case_ids[1]},{case_ids[0]}",
                                "--flush-every-cases",
                                "0",
                            ]
                        ),
                    )
                import pandas as pd

                summary = pd.read_csv(output)
                self.assertEqual(
                    list(case_ids),
                    summary.loc[summary["scope"] == "total", "case_id"].tolist(),
                )


if __name__ == "__main__":
    unittest.main()
