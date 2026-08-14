from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from fmfsolver.gui_spec import solver_spec as fmf_solver_spec
from newtsolver.gui_spec import solver_spec as newt_solver_spec
from panelsolver.app.main_window import MainWindow
from panelsolver.docs_site import DocumentationSiteError


class _Cases(QtWidgets.QWidget):
    vtp_loaded = QtCore.Signal(object)
    viewer_clear_requested = QtCore.Signal()
    cases_updated = QtCore.Signal(object)
    run_finished = QtCore.Signal()

    def logln(self, _message: str) -> None:
        pass

    def selected_case_rows(self):
        return ()

    def is_running(self) -> bool:
        return False


class _Viewer(QtWidgets.QWidget):
    log_message = QtCore.Signal(str)
    save_selected_images_requested = QtCore.Signal()

    def load_vtp(self, *_args) -> None:
        pass

    def clear_view(self) -> None:
        pass

    def set_case_rows(self, _rows) -> None:
        pass

    def save_images_for_case_rows(self, _rows) -> None:
        pass


class _Site:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.pages = []
        self.closed = False

    def resolve(self, page: str = "index.html") -> Path:
        self.pages.append(page)
        return self.root / page

    def close(self) -> None:
        self.closed = True


class _MissingSite(_Site):
    def resolve(self, page: str = "index.html") -> Path:
        raise DocumentationSiteError(f"missing documentation: {page}")


class HelpMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _window(self, spec, site) -> MainWindow:
        return MainWindow(
            spec,
            cases_panel=_Cases(),
            viewer_panel=_Viewer(),
            documentation_site=site,
        )

    def test_three_help_actions_open_home_and_product_selected_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="panel docs ünicode ") as directory:
            root = Path(directory) / "site with spaces"
            (root / "solvers").mkdir(parents=True)
            for page in ("index.html", "solvers/fmfsolver.html", "solvers/newtsolver.html"):
                (root / page).touch()

            for spec_factory, expected_page in (
                (fmf_solver_spec, "solvers/fmfsolver.html"),
                (newt_solver_spec, "solvers/newtsolver.html"),
            ):
                with self.subTest(spec=spec_factory.__module__):
                    site = _Site(root)
                    window = self._window(spec_factory(), site)
                    help_menu = window.help_menu
                    self.assertEqual(
                        [
                            "Documentation Home",
                            "This Solver",
                            "",
                            "About panel-solvers",
                        ],
                        [action.text() for action in help_menu.actions()],
                    )
                    opened = []
                    with patch(
                        "panelsolver.app.main_window.QtGui.QDesktopServices.openUrl",
                        side_effect=lambda url, opened_urls=opened: (
                            opened_urls.append(url) or True
                        ),
                    ):
                        window.documentation_home_action.trigger()
                        window.solver_documentation_action.trigger()
                    self.assertEqual(["index.html", expected_page], site.pages)
                    self.assertEqual(
                        [root / "index.html", root / expected_page],
                        [Path(url.toLocalFile()) for url in opened],
                    )
                    window.close()
                    self.assertTrue(site.closed)

    def test_about_uses_distribution_and_frontend_compatibility_versions(self) -> None:
        site = _Site(Path("site"))
        for spec_factory, compatibility in (
            (fmf_solver_spec, "1.3.8"),
            (newt_solver_spec, "1.0.3"),
        ):
            window = self._window(spec_factory(), site)
            with (
                patch(
                    "panelsolver.app.main_window.importlib.metadata.version",
                    return_value="9.8.7rc1",
                ),
                patch(
                    "panelsolver.app.main_window.QtWidgets.QMessageBox.about"
                ) as about,
            ):
                window.about_action.trigger()
            message = about.call_args.args[2]
            self.assertIn("panel-solvers 9.8.7rc1", message)
            self.assertIn(f"Frontend compatibility: {compatibility}", message)
            self.assertIn(window.spec.product_id, message)
            self.assertIn(window.spec.model_id, message)
            window.close()

    def test_missing_documentation_reports_clear_error(self) -> None:
        window = self._window(fmf_solver_spec(), _MissingSite(Path("site")))
        with patch(
            "panelsolver.app.main_window.QtWidgets.QMessageBox.critical"
        ) as critical:
            window.documentation_home_action.trigger()
        self.assertIn("missing documentation", critical.call_args.args[2])
        window.close()


if __name__ == "__main__":
    unittest.main()
