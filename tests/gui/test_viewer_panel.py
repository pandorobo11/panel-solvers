from __future__ import annotations

import hashlib
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from fmfsolver.gui_spec import solver_spec as fmf_solver_spec
from panelsolver.app import (
    ArtifactSignatureCandidates,
    SolverGuiAdapters,
)
from panelsolver.app.viewer import ViewerPanel
from panelsolver.core import CaseSignature, canonical_json


class FakeCamera:
    def __init__(self) -> None:
        self.position = (1.0, 2.0, 3.0)
        self.focal_point = (0.0, 0.0, 0.0)
        self.up = (0.0, 0.0, 1.0)
        self.clipping_range = (0.1, 10.0)
        self.parallel_projection = False
        self.parallel_scale = 2.0


class FakePlotter:
    def __init__(self) -> None:
        self.interactor = QtWidgets.QWidget()
        self.camera = FakeCamera()
        self.mesh_calls: list[tuple[object, dict[str, object]]] = []
        self.text_calls: list[str] = []
        self.view_vectors: list[tuple[float, float, float]] = []
        self.clear_count = 0
        self.render_count = 0
        self.reset_count = 0
        self.parallel_enabled = False

    def enable_parallel_projection(self) -> None:
        self.parallel_enabled = True
        self.camera.parallel_projection = True

    def clear(self) -> None:
        self.clear_count += 1
        self.mesh_calls.clear()

    def render(self) -> None:
        self.render_count += 1

    def add_mesh(self, poly, **kwargs) -> None:
        self.mesh_calls.append((poly, kwargs))

    def add_text(self, text, **_kwargs):
        self.text_calls.append(text)
        return object()

    def remove_actor(self, _actor) -> None:
        return None

    def add_axes(self) -> None:
        return None

    def reset_camera(self) -> None:
        self.reset_count += 1

    def view_vector(self, vector) -> None:
        self.view_vectors.append(tuple(vector))


class FakePoly:
    def __init__(self, cell_data, field_data=None, indices=None) -> None:
        self.cell_data = {name: np.asarray(value) for name, value in cell_data.items()}
        self.field_data = {} if field_data is None else field_data
        first = next(iter(self.cell_data.values()))
        self.n_cells = len(first) if indices is None else len(indices)
        self._indices = np.arange(len(first)) if indices is None else np.asarray(indices)

    def extract_cells(self, indices):
        selected = self._indices[np.asarray(indices)]
        data = {name: values[selected] for name, values in self.cell_data.items()}
        return FakePoly(data, self.field_data)


def _signature(label: str) -> CaseSignature:
    envelope = {"fixture": label}
    payload = canonical_json(envelope)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return CaseSignature(digest, payload, envelope)


def _adapters(signature: CaseSignature, velocity=(1.0, 0.0, 0.0)):
    return SolverGuiAdapters(
        read_cases=lambda _path: (),
        build_case_signatures=lambda _row: ArtifactSignatureCandidates(signature),
        run_cases=lambda _request: None,
        validate_output_path=lambda out, _input, _rows: Path(out),
        resolve_velocity_hat_stl=lambda _row: velocity,
    )


class ViewerPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def make_viewer(self, *, spec=None, reader=lambda _path: None):
        plotter = FakePlotter()
        viewer = ViewerPanel(
            fmf_solver_spec() if spec is None else spec,
            artifact_reader=reader,
            plotter_factory=lambda _parent: plotter,
        )
        return viewer, plotter

    def test_dynamic_scalars_render_shield_groups_and_overlay(self) -> None:
        viewer, plotter = self.make_viewer()
        poly = FakePoly(
            {
                "model_extra": [4.0, 5.0],
                "shielded": [0, 1],
                "Cp_n": [0.2, 0.4],
            },
            {"case_id": ["case"]},
        )
        loaded = viewer.load_vtp(
            "/tmp/case.vtp",
            poly,
            {"case_id": "case", "S": 5.0, "Ti_K": 300.0},
        )
        self.assertTrue(loaded)
        self.assertEqual(
            ["Cp_n", "shielded", "model_extra"],
            [viewer.cmb_scalar.itemText(i) for i in range(viewer.cmb_scalar.count())],
        )
        self.assertEqual("Cp_n", viewer.cmb_scalar.currentText())
        self.assertEqual(2, len(plotter.mesh_calls))
        self.assertEqual(1.0, plotter.mesh_calls[0][1]["opacity"])
        self.assertEqual(0.30, plotter.mesh_calls[1][1]["opacity"])
        self.assertEqual("jet", plotter.mesh_calls[0][1]["cmap"])
        self.assertEqual((0.2, 0.4), plotter.mesh_calls[0][1]["clim"])
        self.assertIn("case_id=case", plotter.text_calls[-1])
        self.assertTrue(plotter.parallel_enabled)

    def test_reload_uses_first_available_preferred_scalar(self) -> None:
        viewer, _plotter = self.make_viewer()
        viewer.load_vtp("/tmp/first.vtp", FakePoly({"Cp_n": [1.0]}))
        viewer.load_vtp(
            "/tmp/second.vtp",
            FakePoly({"model_extra": [3.0], "shielded": [0]}),
        )
        self.assertEqual("shielded", viewer.cmb_scalar.currentText())
        self.assertEqual((0.0, 1.0), viewer._automatic_limits("shielded"))

    def test_redraw_preserves_camera_and_buttons_set_expected_vectors(self) -> None:
        viewer, plotter = self.make_viewer()
        viewer.load_vtp("/tmp/case.vtp", FakePoly({"Cp_n": [1.0]}))
        plotter.camera.position = (9.0, 8.0, 7.0)
        viewer.chk_edges.setChecked(False)
        self.assertEqual((9.0, 8.0, 7.0), plotter.camera.position)
        viewer.btn_view_xp.click()
        viewer.btn_view_iso_2.click()
        self.assertEqual((1, 0, 0), plotter.view_vectors[-2])
        self.assertEqual((1, -1, -1), plotter.view_vectors[-1])

    def test_wind_views_use_only_the_injected_spec_adapter(self) -> None:
        signature = _signature("wind")
        viewer, plotter = self.make_viewer(
            spec=fmf_solver_spec(adapters=_adapters(signature, (2.0, 0.0, 0.0)))
        )
        viewer.load_vtp(
            "/tmp/case.vtp",
            FakePoly({"Cp_n": [1.0]}),
            {"case_id": "case"},
        )
        viewer.set_view_wind()
        viewer.set_view_wind_reverse()
        self.assertEqual((-1.0, -0.0, -0.0), plotter.view_vectors[-2])
        self.assertEqual((1.0, 0.0, 0.0), plotter.view_vectors[-1])

    def test_manual_stale_artifact_displays_without_case_context(self) -> None:
        current = _signature("current")
        stale = _signature("stale")
        viewer, plotter = self.make_viewer(
            spec=fmf_solver_spec(adapters=_adapters(current))
        )
        viewer.set_case_rows(({"case_id": "case"},))
        poly = FakePoly(
            {"Cp_n": [1.0]},
            {"case_id": ["case"], "case_signature": [stale.digest]},
        )
        self.assertTrue(viewer.load_vtp("/tmp/stale.vtp", poly))
        self.assertIsNone(viewer._display_case_row)
        self.assertEqual("case_id=case", plotter.text_calls[-1])

    def test_failed_read_and_invalid_cell_data_clear_previous_view(self) -> None:
        def broken(_path):
            raise ValueError("broken")

        viewer, plotter = self.make_viewer(reader=broken)
        viewer.load_vtp("/tmp/good.vtp", FakePoly({"Cp_n": [1.0]}))
        messages: list[str] = []
        viewer.log_message.connect(messages.append)
        self.assertFalse(viewer.load_vtp("/tmp/broken.vtp"))
        self.assertIsNone(viewer._poly)
        self.assertEqual(0, viewer.cmb_scalar.count())
        self.assertIn("Failed to read VTP", messages[-1])
        self.assertGreaterEqual(plotter.clear_count, 2)
        self.assertFalse(
            viewer.load_vtp("/tmp/empty.vtp", SimpleNamespace(cell_data={}, n_cells=0))
        )
        self.assertIn("Invalid VTP cell data", messages[-1])

    def test_dialog_manual_open_and_range_controls(self) -> None:
        poly = FakePoly({"Cp_n": [1.0, 3.0]})
        viewer, _plotter = self.make_viewer(reader=lambda _path: poly)
        with patch.object(
            QtWidgets.QFileDialog,
            "getOpenFileName",
            return_value=("/tmp/manual.vtp", "VTK"),
        ):
            viewer.open_vtp()
        self.assertEqual(Path("/tmp/manual.vtp"), viewer._loaded_vtp_path)
        viewer.edit_vmin.setText("0")
        viewer.edit_vmax.setText("10")
        self.assertEqual((0.0, 10.0), viewer._automatic_limits("Cp_n"))
        viewer.clear_range()
        self.assertEqual("", viewer.edit_vmin.text())
        self.assertEqual("", viewer.edit_vmax.text())


if __name__ == "__main__":
    unittest.main()
