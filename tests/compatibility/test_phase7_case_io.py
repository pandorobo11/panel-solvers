import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import numpy as np
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
from panelsolver.core import MeshValidationPolicy, ResultCache, execute_case

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
                    if filename == "fmf_beta_tan_90.csv":
                        self.assertEqual(["alpha_deg"], [issue.field for issue in error.issues])
                        continue
                    self.assertEqual(expected["message"], str(error))
                    self.assertEqual(
                        expected["issues"],
                        [asdict(issue) for issue in error.issues],
                    )

    def test_excel_engine_dispatch_is_common(self) -> None:
        for reader, filename in (
            (read_fmf_cases, "fmfsolver_cases.csv"),
            (read_newt_cases, "newtsolver_cases.csv"),
        ):
            frame = reader(_INPUTS / filename)
            for suffix, engine in (
                (".xls", "xlrd"),
                (".xlsx", "openpyxl"),
                (".xlsm", "openpyxl"),
            ):
                with self.subTest(filename=filename, suffix=suffix), patch(
                    "panelsolver.app.case_io.pd.read_excel",
                    return_value=frame.copy(),
                ) as read_excel:
                    reader(f"cases{suffix}")
                    self.assertEqual(engine, read_excel.call_args.kwargs["engine"])
                    self.assertEqual(
                        {"case_id": "string"}, read_excel.call_args.kwargs["dtype"]
                    )

    def test_csv_xlsx_xlsm_and_biff_xls_preserve_valid_rows(self) -> None:
        for reader, stem, row_count in (
            (read_fmf_cases, "fmfsolver_cases", 6),
            (read_newt_cases, "newtsolver_cases", 9),
        ):
            csv_frame = reader(_INPUTS / f"{stem}.csv")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp = Path(temp_dir)
                xlsx = temp / f"{stem}.xlsx"
                xlsm = temp / f"{stem}.xlsm"
                csv_frame.to_excel(xlsx, index=False, engine="openpyxl")
                xlsm.write_bytes(xlsx.read_bytes())
                for path in (
                    _INPUTS / f"{stem}.csv",
                    _INPUTS / f"{stem}.xls",
                    xlsx,
                    xlsm,
                ):
                    with self.subTest(stem=stem, suffix=path.suffix):
                        actual = reader(path)
                        self.assertEqual(row_count, len(actual))
                        self.assertEqual(
                            csv_frame["case_id"].tolist(), actual["case_id"].tolist()
                        )
                        self.assertEqual(list(csv_frame.columns), list(actual.columns))

    def test_case_ids_use_one_portable_unicode_and_casefold_policy(self) -> None:
        products = (
            (read_fmf_cases, "fmfsolver_cases.csv"),
            (read_newt_cases, "newtsolver_cases.csv"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for reader, filename in products:
                base = reader(_INPUTS / filename).iloc[[0]].copy()
                path = temp / filename
                for accepted in ("日本語", "Straße-ケース"):
                    with self.subTest(filename=filename, accepted=accepted):
                        frame = base.copy()
                        frame.loc[frame.index[0], "case_id"] = accepted
                        frame.to_csv(path, index=False)
                        self.assertEqual(accepted, reader(path).iloc[0]["case_id"])
                for rejected in (
                    "",
                    ".",
                    "..",
                    "a/b",
                    "a\\b",
                    "a:name",
                    "a\nb",
                    "CON",
                    "con.txt",
                    "name.",
                    "name ",
                ):
                    with self.subTest(filename=filename, rejected=rejected):
                        frame = base.copy()
                        frame.loc[frame.index[0], "case_id"] = rejected
                        frame.to_csv(path, index=False)
                        with self.assertRaises(Exception) as caught:
                            reader(path)
                        self.assertEqual(
                            "InputValidationError", type(caught.exception).__name__
                        )
                        self.assertIn(
                            "case_id", [issue.field for issue in caught.exception.issues]
                        )

                duplicates = pd.concat([base, base], ignore_index=True)
                duplicates.loc[0, "case_id"] = "Straße"
                duplicates.loc[1, "case_id"] = "STRASSE"
                duplicates.to_csv(path, index=False)
                with self.assertRaisesRegex(Exception, "Unicode casefold"):
                    reader(path)

    def test_attitude_domains_are_common_and_mode_specific(self) -> None:
        products = (
            (read_fmf_cases, "fmfsolver_cases.csv"),
            (read_newt_cases, "newtsolver_cases.csv"),
        )
        rejected = (
            ("beta_tan", "alpha_deg", -90.0),
            ("beta_tan", "alpha_deg", 90.0),
            ("beta_tan", "beta_or_bank_deg", -90.0),
            ("beta_tan", "beta_or_bank_deg", 90.0),
            ("beta_sin", "alpha_deg", -90.0),
            ("beta_sin", "alpha_deg", 90.0),
        )
        accepted = (
            ("beta_tan", 89.999, -89.999),
            ("beta_sin", 89.999, 90.0),
            ("bank", 180.0, 1080.0),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            for reader, filename in products:
                base = reader(_INPUTS / filename).iloc[[0]].copy()
                base[["alpha_deg", "beta_or_bank_deg"]] = base[
                    ["alpha_deg", "beta_or_bank_deg"]
                ].astype(float)
                path = temp / filename
                for mode, field, value in rejected:
                    with self.subTest(filename=filename, mode=mode, field=field):
                        frame = base.copy()
                        frame.loc[frame.index[0], "attitude_input"] = mode
                        frame.loc[frame.index[0], field] = value
                        frame.to_csv(path, index=False)
                        with self.assertRaises(Exception) as caught:
                            reader(path)
                        self.assertIn(
                            field, [issue.field for issue in caught.exception.issues]
                        )
                for mode, alpha, beta_or_bank in accepted:
                    with self.subTest(filename=filename, mode=mode, accepted=True):
                        frame = base.copy()
                        frame.loc[frame.index[0], "attitude_input"] = mode
                        frame.loc[frame.index[0], "alpha_deg"] = alpha
                        frame.loc[frame.index[0], "beta_or_bank_deg"] = beta_or_bank
                        frame.to_csv(path, index=False)
                        actual = reader(path).iloc[0]
                        self.assertEqual(mode, actual["attitude_input"])


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

    def test_equivalent_attitude_modes_keep_exact_cache_entries_separate(self) -> None:
        frame = read_newt_cases(_INPUTS / "newtsolver_cases.csv")
        beta_sin = frame.loc[
            frame["case_id"] == "newt_beta_sin_boundary"
        ].iloc[0].to_dict()
        beta_tan = dict(beta_sin)
        beta_tan["attitude_input"] = "beta_tan"

        adapted_sin = adapt_newt_row(beta_sin)
        adapted_tan = adapt_newt_row(beta_tan)
        self.assertEqual(
            (
                adapted_sin.attitude.alpha_t_deg,
                adapted_sin.attitude.beta_t_deg,
            ),
            (
                adapted_tan.attitude.alpha_t_deg,
                adapted_tan.attitude.beta_t_deg,
            ),
        )
        self.assertFalse(
            np.array_equal(
                adapted_sin.attitude.velocity_hat_stl,
                adapted_tan.attitude.velocity_hat_stl,
            )
        )

        cache = ResultCache(max_entries=2)
        first_sin = execute_case(adapted_sin.request, result_cache=cache)
        first_tan = execute_case(adapted_tan.request, result_cache=cache)
        cached_sin = execute_case(adapted_sin.request, result_cache=cache)
        cached_tan = execute_case(adapted_tan.request, result_cache=cache)

        self.assertEqual(first_sin.signature.digest, first_tan.signature.digest)
        self.assertEqual(
            [False, False, True, True],
            [
                first_sin.cache_hit,
                first_tan.cache_hit,
                cached_sin.cache_hit,
                cached_tan.cache_hit,
            ],
        )
        self.assertFalse(
            np.array_equal(
                first_sin.results.local_loads.traction_coeff_stl,
                first_tan.results.local_loads.traction_coeff_stl,
            )
        )
        self.assertEqual(
            (2, 2, 2),
            (cache.stats().entries, cache.stats().hits, cache.stats().misses),
        )


if __name__ == "__main__":
    unittest.main()
