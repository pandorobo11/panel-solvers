from __future__ import annotations

import importlib
import importlib.metadata
import unittest


class Phase6GuiPackageTests(unittest.TestCase):
    def test_legacy_gui_modules_and_shared_bootstrap_are_importable(self) -> None:
        for module_name in (
            "panelsolver.app.gui_bootstrap",
            "panelsolver.app.main_window",
            "panelsolver.app.viewer",
            "panelsolver.gui",
            "fmfsolver.app.gui_app",
            "newtsolver.app.gui_app",
        ):
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_canonical_and_all_phase7_legacy_commands_are_registered(self) -> None:
        expected_commands = {
            "panelsolver": "panelsolver.cli:main",
            "panelsolver-gui": "panelsolver.gui:main",
            "fmfsolver": "fmfsolver.app.gui_app:main",
            "fmfsolver-gui": "fmfsolver.app.gui_app:main",
            "fmfsolver-cli": "fmfsolver.app.cli_app:main",
            "newtsolver": "newtsolver.app.gui_app:main",
            "newtsolver-gui": "newtsolver.app.gui_app:main",
            "newtsolver-cli": "newtsolver.app.cli_app:main",
        }
        distribution = importlib.metadata.distribution("panel-solvers")
        registered = {
            entry.name: entry.value
            for entry in distribution.entry_points
            if entry.group == "console_scripts"
        }
        self.assertEqual(expected_commands, registered)


if __name__ == "__main__":
    unittest.main()
