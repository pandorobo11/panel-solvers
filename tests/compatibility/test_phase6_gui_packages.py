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
            "fmfsolver.app.gui_app",
            "newtsolver.app.gui_app",
        ):
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_phase7_legacy_commands_are_not_registered(self) -> None:
        legacy_commands = {
            "fmfsolver",
            "fmfsolver-gui",
            "fmfsolver-cli",
            "newtsolver",
            "newtsolver-gui",
            "newtsolver-cli",
        }
        distribution = importlib.metadata.distribution("panel-solvers")
        registered = {
            entry.name
            for entry in distribution.entry_points
            if entry.group == "console_scripts"
        }
        self.assertTrue(legacy_commands.isdisjoint(registered))


if __name__ == "__main__":
    unittest.main()
