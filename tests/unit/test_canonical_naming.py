from __future__ import annotations

import ast
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CanonicalNamingTests(unittest.TestCase):
    def test_current_docs_and_examples_use_domain_paths(self) -> None:
        for relative_path in (
            "docs/solvers/fmf.md",
            "docs/solvers/hypersonic.md",
            "docs/reference/fmf-input.md",
            "docs/reference/hypersonic-input.md",
            "examples/fmf",
            "examples/hypersonic",
        ):
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).exists())

        for relative_path in (
            "docs/solvers/fmfsolver.md",
            "docs/solvers/newtsolver.md",
            "docs/reference/fmfsolver-input.md",
            "docs/reference/newtsolver-input.md",
            "examples/fmfsolver",
            "examples/newtsolver",
        ):
            with self.subTest(legacy_path=relative_path):
                self.assertFalse((ROOT / relative_path).exists())

    def test_current_example_regression_imports_canonical_domains(self) -> None:
        path = ROOT / "tests" / "regression" / "test_examples.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        from_imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        direct_imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports = from_imports | direct_imports
        self.assertIn("panelsolver.domains", from_imports)
        self.assertFalse(
            any(
                module == legacy or module.startswith(f"{legacy}.")
                for module in imports
                for legacy in ("fmfsolver", "newtsolver")
            )
        )

    def test_current_example_case_ids_do_not_use_legacy_product_names(self) -> None:
        for domain in ("fmf", "hypersonic"):
            for path in sorted((ROOT / "examples" / domain).glob("*.csv")):
                with path.open(encoding="utf-8", newline="") as stream:
                    for row in csv.DictReader(stream):
                        with self.subTest(path=path.relative_to(ROOT), row=row):
                            case_id = row["case_id"].casefold()
                            self.assertFalse(case_id.startswith("fmfsolver"))
                            self.assertFalse(case_id.startswith("newtsolver"))

    def test_docs_plot_outputs_use_hypersonic_filenames(self) -> None:
        assets = ROOT / "docs" / "assets" / "plots"
        expected = (
            "hypersonic-windward-cp-vs-angle.svg",
            "hypersonic-leeward-cp-vs-angle.svg",
        )
        legacy = (
            "newtsolver-windward-cp-vs-angle.svg",
            "newtsolver-leeward-cp-vs-angle.svg",
        )
        generator = (
            ROOT / "scripts" / "generate_docs_angle_response_plots.py"
        ).read_text(encoding="utf-8")
        for filename in expected:
            with self.subTest(filename=filename):
                self.assertTrue((assets / filename).is_file())
                self.assertIn(f'"{filename}"', generator)
        for filename in legacy:
            with self.subTest(legacy_filename=filename):
                self.assertFalse((assets / filename).exists())
                self.assertNotIn(filename, generator)


if __name__ == "__main__":
    unittest.main()
