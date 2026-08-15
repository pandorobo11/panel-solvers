from __future__ import annotations

import importlib.metadata
import unittest

from panelsolver.app.versioning import panel_solvers_distribution_version


class VersioningTests(unittest.TestCase):
    def test_artifact_version_source_is_installed_distribution_metadata(self) -> None:
        self.assertEqual(
            importlib.metadata.version("panel-solvers"),
            panel_solvers_distribution_version(),
        )


if __name__ == "__main__":
    unittest.main()
