from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from panelsolver.docs_site import (
    DocumentationSite,
    build_documentation_site,
    validate_documentation_page,
)


class DocumentationSiteTests(unittest.TestCase):
    def test_strict_site_build_contains_offline_solver_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="panel docs ünicode ") as directory:
            site = Path(directory) / "offline site"
            build_documentation_site(Path.cwd(), site)
            for page in (
                "index.html",
                "solvers/fmfsolver.html",
                "solvers/newtsolver.html",
            ):
                self.assertTrue((site / page).is_file(), page)
            index = (site / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("https://cdn", index.lower())
            self.assertIn("getting-started/installation.html", index)

    def test_page_validation_accepts_only_normalized_relative_html(self) -> None:
        self.assertEqual(
            "solvers/fmfsolver.html",
            validate_documentation_page(" solvers/fmfsolver.html "),
        )
        for value in (
            None,
            "",
            "/index.html",
            "C:\\index.html",
            "../index.html",
            "solvers/../index.html",
            "solvers\\index.html",
            "solvers//fmfsolver.html",
            "solvers/fmfsolver.md",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_documentation_page(value)

    def test_editable_checkout_fallback_builds_and_caches_site(self) -> None:
        site = DocumentationSite()
        try:
            index = site.resolve()
            self.assertTrue(index.is_file())
            self.assertEqual(index.parent, site.resolve().parent)
            self.assertTrue(site.resolve("solvers/newtsolver.html").is_file())
        finally:
            site.close()


if __name__ == "__main__":
    unittest.main()
