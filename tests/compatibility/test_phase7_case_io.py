import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from fmfsolver.case_adapter import (
    FMFSOLVER_COMPATIBILITY_VERSION,
)
from fmfsolver.case_adapter import (
    adapt_row as adapt_fmf_row,
)
from fmfsolver.case_adapter import (
    build_signatures as build_fmf_signatures,
)
from fmfsolver.io.io_cases import read_cases as read_fmf_cases
from newtsolver.case_adapter import (
    NEWTSOLVER_COMPATIBILITY_VERSION,
)
from newtsolver.case_adapter import (
    adapt_row as adapt_newt_row,
)
from newtsolver.case_adapter import (
    build_signatures as build_newt_signatures,
)
from newtsolver.io.io_cases import read_cases as read_newt_cases
from panelsolver.core import MeshValidationPolicy, execute_case

_INPUTS = Path(__file__).parents[1] / "fixtures" / "phase1" / "inputs"
_GOLDEN = Path(__file__).parents[1] / "fixtures" / "phase1" / "golden"


class ProductCaseReaderTests(unittest.TestCase):
    def test_valid_phase1_tables_preserve_rows_columns_defaults_and_paths(self) -> None:
        products = (
            ("fmfsolver", read_fmf_cases, "fmfsolver_cases.csv", 6),
            ("newtsolver", read_newt_cases, "newtsolver_cases.csv", 9),
        )
        for product, reader, filename, row_count in products:
            with self.subTest(product=product):
                frame = reader(_INPUTS / filename)
                contract = json.loads(
                    (_GOLDEN / product / "contracts.json").read_text()
                )
                expected_columns = contract["cli_run"]["result_csv_columns"][
                    : len(frame.columns)
                ]
                self.assertEqual(row_count, len(frame))
                self.assertEqual(expected_columns, list(frame.columns))
                self.assertTrue(frame["stl_path"].map(Path).map(Path.is_absolute).all())
                self.assertTrue(frame["out_dir"].map(Path).map(Path.is_absolute).all())

    def test_invalid_phase1_tables_preserve_structured_issue_contracts(self) -> None:
        for product, reader in (
            ("fmfsolver", read_fmf_cases),
            ("newtsolver", read_newt_cases),
        ):
            contract = json.loads(
                (_GOLDEN / product / "contracts.json").read_text()
            )
            for filename, expected in contract["invalid_inputs"].items():
                with self.subTest(product=product, filename=filename):
                    with self.assertRaises(Exception) as caught:
                        reader(_INPUTS / "invalid" / filename)
                    error = caught.exception
                    self.assertEqual("InputValidationError", type(error).__name__)
                    self.assertEqual(expected["message"], str(error))
                    self.assertEqual(
                        expected["issues"],
                        [asdict(issue) for issue in error.issues],
                    )

    def test_xls_dispatch_remains_product_specific(self) -> None:
        fmf_frame = read_fmf_cases(_INPUTS / "fmfsolver_cases.csv")
        newt_frame = read_newt_cases(_INPUTS / "newtsolver_cases.csv")
        with patch(
            "panelsolver.app.case_io.pd.read_excel",
            return_value=fmf_frame.copy(),
        ) as read_excel:
            read_fmf_cases("cases.xls")
            self.assertEqual("xlrd", read_excel.call_args.kwargs["engine"])
        with patch(
            "panelsolver.app.case_io.pd.read_excel",
            return_value=newt_frame.copy(),
        ) as read_excel:
            read_newt_cases("cases.xls")
            self.assertEqual("openpyxl", read_excel.call_args.kwargs["engine"])

    def test_case_id_duplicate_and_angle_policies_are_not_unified(self) -> None:
        fmf = read_fmf_cases(_INPUTS / "fmfsolver_cases.csv").iloc[[0]].copy()
        newt = read_newt_cases(_INPUTS / "newtsolver_cases.csv").iloc[[0]].copy()
        fmf.loc[fmf.index[0], "case_id"] = "日本語"
        newt.loc[newt.index[0], "case_id"] = "日本語"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fmf_path = temp / "fmf.csv"
            newt_path = temp / "newt.csv"
            fmf.to_csv(fmf_path, index=False)
            newt.to_csv(newt_path, index=False)
            self.assertEqual("日本語", read_fmf_cases(fmf_path).iloc[0]["case_id"])
            with self.assertRaisesRegex(Exception, "ASCII"):
                read_newt_cases(newt_path)

            fmf_dupes = pd.concat([fmf, fmf], ignore_index=True)
            fmf_dupes.loc[0, "case_id"] = "Case"
            fmf_dupes.loc[1, "case_id"] = "case"
            newt_dupes = pd.concat([newt, newt], ignore_index=True)
            newt_dupes.loc[0, "case_id"] = "Case"
            newt_dupes.loc[1, "case_id"] = "case"
            fmf_dupes.to_csv(fmf_path, index=False)
            newt_dupes.to_csv(newt_path, index=False)
            self.assertEqual(2, len(read_fmf_cases(fmf_path)))
            with self.assertRaisesRegex(Exception, "case-insensitive"):
                read_newt_cases(newt_path)

            newt.loc[newt.index[0], "case_id"] = "angle90"
            newt.loc[newt.index[0], "alpha_deg"] = 90.0
            newt.to_csv(newt_path, index=False)
            row = read_newt_cases(newt_path).iloc[0].to_dict()
            self.assertEqual(90.0, adapt_newt_row(row).attitude.alpha_t_deg)


class ProductCaseAdapterTests(unittest.TestCase):
    def test_rows_bind_independent_models_mesh_policies_and_environment_prefixes(self) -> None:
        fmf_row = read_fmf_cases(_INPUTS / "fmfsolver_cases.csv").iloc[0].to_dict()
        newt_row = read_newt_cases(_INPUTS / "newtsolver_cases.csv").iloc[0].to_dict()
        fmf = adapt_fmf_row(fmf_row)
        newt = adapt_newt_row(newt_row)
        self.assertEqual("sentman", fmf.request.model_case.model_id)
        self.assertEqual(MeshValidationPolicy.STRICT, fmf.request.mesh_validation_policy)
        self.assertEqual("FMFSOLVER", fmf.request.shielding.legacy_env_prefix)
        self.assertEqual("hypersonic", newt.request.model_case.model_id)
        self.assertEqual(
            MeshValidationPolicy.LEGACY_WARN_REPAIR,
            newt.request.mesh_validation_policy,
        )
        self.assertEqual("NEWTSOLVER", newt.request.shielding.legacy_env_prefix)
        self.assertEqual("1.3.8", FMFSOLVER_COMPATIBILITY_VERSION)
        self.assertEqual("1.0.3", NEWTSOLVER_COMPATIBILITY_VERSION)

    def test_prepared_primary_signature_is_exactly_the_execution_signature(self) -> None:
        cases = (
            (
                read_fmf_cases(_INPUTS / "fmfsolver_cases.csv").iloc[0].to_dict(),
                adapt_fmf_row,
                build_fmf_signatures,
            ),
            (
                read_newt_cases(_INPUTS / "newtsolver_cases.csv").iloc[0].to_dict(),
                adapt_newt_row,
                build_newt_signatures,
            ),
        )
        for row, adapter, signature_builder in cases:
            with self.subTest(case_id=row["case_id"]):
                candidates = signature_builder(row)
                result = execute_case(adapter(row).request)
                self.assertEqual(result.signature, candidates.primary)
                self.assertGreaterEqual(len(candidates.legacy_signatures), 1)

    def test_direct_and_default_normalized_legacy_candidates_stay_ordered(self) -> None:
        for frame, builder in (
            (
                read_fmf_cases(_INPUTS / "fmfsolver_cases.csv"),
                build_fmf_signatures,
            ),
            (
                read_newt_cases(_INPUTS / "newtsolver_cases.csv"),
                build_newt_signatures,
            ),
        ):
            row = frame.iloc[0].to_dict()
            row.pop("attitude_input")
            with self.subTest(case_id=row["case_id"]):
                candidates = builder(row)
                self.assertEqual(2, len(candidates.legacy_signatures))
                self.assertNotEqual(*candidates.legacy_signatures)


if __name__ == "__main__":
    unittest.main()
