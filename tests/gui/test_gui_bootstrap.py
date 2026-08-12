from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from fmfsolver.app import gui_app as fmf_gui_app
from fmfsolver.gui_spec import solver_spec as fmf_solver_spec
from newtsolver.app import gui_app as newt_gui_app
from newtsolver.gui_spec import solver_spec as newt_solver_spec
from panelsolver.app import ClosePolicy, GuiRunResult, SolverGuiAdapters
from panelsolver.app.gui_bootstrap import (
    GuiAdaptersUnavailable,
    create_main_window,
    prepare_gui_spec,
    run_gui,
)


class _FakeCases:
    def __init__(self) -> None:
        self.messages = []

    def logln(self, message: str) -> None:
        self.messages.append(message)


class _FakeWindow:
    def __init__(self, spec) -> None:
        self.spec = spec
        self.cases_panel = _FakeCases()
        self.shown = False

    def show(self) -> None:
        self.shown = True


def _adapters() -> SolverGuiAdapters:
    return SolverGuiAdapters(
        read_cases=lambda _path: (),
        build_case_signatures=lambda _row: (),
        run_cases=lambda _request: GuiRunResult(),
        validate_output_path=lambda out, _input, _rows: Path(out),
        resolve_velocity_hat_stl=lambda _row: (1.0, 0.0, 0.0),
    )


class GuiBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_prepare_preserves_complete_spec_and_adds_only_unavailable_adapters(self) -> None:
        complete = fmf_solver_spec(adapters=_adapters())
        self.assertIs(complete, prepare_gui_spec(complete))

        selected = newt_solver_spec()
        runtime = prepare_gui_spec(selected)
        self.assertIsNot(selected, runtime)
        for field in (
            "product_id",
            "model_id",
            "window_title",
            "case_columns",
            "preferred_scalars",
            "format_case",
            "close_policy",
        ):
            self.assertEqual(getattr(selected, field), getattr(runtime, field))
        with self.assertRaisesRegex(GuiAdaptersUnavailable, "Phase 7"):
            runtime.adapters.read_cases("cases.csv")

    def test_create_window_records_phase7_gap_without_product_branch(self) -> None:
        window = create_main_window(fmf_solver_spec(), window_factory=_FakeWindow)
        self.assertEqual("fmfsolver", window.spec.product_id)
        self.assertIsNotNone(window.spec.adapters)
        self.assertIn("Phase 7", window.cases_panel.messages[-1])

    def test_run_gui_uses_shared_window_and_event_loop(self) -> None:
        made = []

        def factory(spec):
            window = _FakeWindow(spec)
            made.append(window)
            return window

        with patch.object(QtWidgets.QApplication, "exec", return_value=23) as execute:
            self.assertEqual(23, run_gui(fmf_solver_spec(), window_factory=factory))
        execute.assert_called_once_with()
        self.assertTrue(made[0].shown)
        self.assertEqual("sentman", made[0].spec.model_id)

    def test_compatibility_launchers_select_independent_specs_only(self) -> None:
        captured = []

        def fake_run(spec):
            captured.append(spec)
            return len(captured)

        with patch(
            "panelsolver.app.gui_bootstrap.run_gui",
            side_effect=fake_run,
        ):
            with self.assertRaises(SystemExit) as fmf_exit:
                fmf_gui_app.main()
            with self.assertRaises(SystemExit) as newt_exit:
                newt_gui_app.main()
        self.assertEqual(1, fmf_exit.exception.code)
        self.assertEqual(2, newt_exit.exception.code)
        fmf, newt = captured
        self.assertEqual("Sentman FMF Solver (GUI)", fmf.window_title)
        self.assertEqual("sentman", fmf.model_id)
        self.assertEqual(ClosePolicy.DEFER_UNTIL_IDLE, fmf.close_policy)
        self.assertIn("S", fmf.case_columns)
        self.assertNotIn("gamma", fmf.case_columns)
        self.assertEqual("newtsolver (GUI)", newt.window_title)
        self.assertEqual("hypersonic", newt.model_id)
        self.assertEqual(ClosePolicy.IMMEDIATE, newt.close_policy)
        self.assertIn("gamma", newt.case_columns)
        self.assertNotIn("S", newt.case_columns)
        self.assertEqual(fmf.preferred_scalars, newt.preferred_scalars)
        self.assertIsNot(fmf.format_case, newt.format_case)


if __name__ == "__main__":
    unittest.main()
