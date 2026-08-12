"""Shared Qt/PyVista VTP viewer driven by :class:`SolverSpec`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import pyvista as pv
from PySide6 import QtCore, QtWidgets
from pyvistaqt import QtInteractor

from .solver_spec import CaseRow, SolverSpec
from .viewer_data import (
    ScalarField,
    discover_scalar_fields,
    field_data_scalar,
    resolve_matching_case_row,
    scalar_color_limits,
)


class ViewerPanel(QtWidgets.QWidget):
    """Render VTP cell data without owning product or numerical behavior."""

    log_message = QtCore.Signal(str)

    def __init__(
        self,
        spec: SolverSpec,
        parent=None,
        *,
        artifact_reader: Callable[[str], object] = pv.read,
        plotter_factory: Callable[[QtWidgets.QWidget], object] = QtInteractor,
    ) -> None:
        if not isinstance(spec, SolverSpec):
            raise TypeError("spec must be a SolverSpec")
        if not callable(artifact_reader):
            raise TypeError("artifact_reader must be callable")
        if not callable(plotter_factory):
            raise TypeError("plotter_factory must be callable")
        super().__init__(parent)
        self.spec = spec
        self._artifact_reader = artifact_reader
        self._root_layout = QtWidgets.QVBoxLayout(self)
        self._root_layout.setSpacing(6)
        self._root_layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = plotter_factory(self)
        self._enable_parallel_projection()
        interactor = getattr(self.plotter, "interactor", None)
        if not isinstance(interactor, QtWidgets.QWidget):
            raise TypeError("plotter_factory must provide a QWidget interactor")
        self._root_layout.addWidget(interactor, 6)

        self._init_controls()
        self._build_controls_layout()
        self._connect_controls()

        self._case_rows: tuple[CaseRow, ...] = ()
        self._poly: object | None = None
        self._loaded_vtp_path: Path | None = None
        self._display_case_row: CaseRow | None = None
        self._scalar_fields: dict[str, ScalarField] = {}
        self._overlay_actor = None
        self._default_view_vec = (-1, -1, 1)
        self._camera_initialized = False

    def _enable_parallel_projection(self) -> None:
        try:
            self.plotter.enable_parallel_projection()
            return
        except Exception:
            pass
        try:
            self.plotter.camera.parallel_projection = True
        except Exception:
            pass

    def _init_controls(self) -> None:
        self.cmb_scalar = QtWidgets.QComboBox()
        self.cmb_scalar.setMinimumWidth(145)
        self.chk_edges = QtWidgets.QCheckBox("Show edges")
        self.chk_edges.setChecked(True)
        self.chk_shield_transparent = QtWidgets.QCheckBox("Shielded transparent")
        self.chk_shield_transparent.setChecked(True)
        self.chk_overlay_text = QtWidgets.QCheckBox("Show info text")
        self.chk_overlay_text.setChecked(True)
        self.cmb_cmap = QtWidgets.QComboBox()
        self.cmb_cmap.addItems(["jet", "viridis", "bwr"])
        self.cmb_cmap.setCurrentText("jet")
        self.edit_vmin = QtWidgets.QLineEdit()
        self.edit_vmax = QtWidgets.QLineEdit()
        self.edit_vmin.setPlaceholderText("vmin (blank=auto)")
        self.edit_vmax.setPlaceholderText("vmax (blank=auto)")
        self.btn_auto_range = QtWidgets.QPushButton("Auto range")
        self.btn_open_vtp = QtWidgets.QPushButton("Open VTP...")
        self.btn_view_xp = QtWidgets.QPushButton("+X")
        self.btn_view_xn = QtWidgets.QPushButton("-X")
        self.btn_view_yp = QtWidgets.QPushButton("+Y")
        self.btn_view_yn = QtWidgets.QPushButton("-Y")
        self.btn_view_zp = QtWidgets.QPushButton("+Z")
        self.btn_view_zn = QtWidgets.QPushButton("-Z")
        self.btn_view_iso_1 = QtWidgets.QPushButton("-X -Y +Z")
        self.btn_view_iso_2 = QtWidgets.QPushButton("+X -Y -Z")
        self.btn_view_wind = QtWidgets.QPushButton("Wind +")
        self.btn_view_wind_rev = QtWidgets.QPushButton("Wind -")

    def _build_controls_layout(self) -> None:
        controls = QtWidgets.QVBoxLayout()
        controls.setSpacing(3)
        controls.setContentsMargins(0, 0, 0, 0)

        display = QtWidgets.QHBoxLayout()
        display.addWidget(QtWidgets.QLabel("Scalar"))
        display.addWidget(self.cmb_scalar)
        display.addSpacing(10)
        display.addWidget(QtWidgets.QLabel("Colormap"))
        display.addWidget(self.cmb_cmap)
        display.addStretch(1)
        display.addWidget(self.btn_open_vtp)

        options = QtWidgets.QHBoxLayout()
        options.addWidget(QtWidgets.QLabel("Display"))
        options.addWidget(self.chk_edges)
        options.addWidget(self.chk_shield_transparent)
        options.addWidget(self.chk_overlay_text)
        options.addStretch(1)

        colorbar = QtWidgets.QHBoxLayout()
        colorbar.addWidget(QtWidgets.QLabel("Colorbar"))
        colorbar.addWidget(self.edit_vmin)
        colorbar.addWidget(self.edit_vmax)
        colorbar.addWidget(self.btn_auto_range)
        colorbar.addStretch(1)

        camera = QtWidgets.QHBoxLayout()
        camera.addWidget(QtWidgets.QLabel("Camera"))
        for button in (
            self.btn_view_xp,
            self.btn_view_xn,
            self.btn_view_yp,
            self.btn_view_yn,
            self.btn_view_zp,
            self.btn_view_zn,
            self.btn_view_iso_1,
            self.btn_view_iso_2,
            self.btn_view_wind,
            self.btn_view_wind_rev,
        ):
            camera.addWidget(button)
        camera.addStretch(1)

        controls.addLayout(display)
        controls.addLayout(options)
        controls.addLayout(colorbar)
        controls.addLayout(camera)
        self._root_layout.addLayout(controls)

    def _connect_controls(self) -> None:
        self.btn_open_vtp.clicked.connect(self.open_vtp)
        self.cmb_scalar.currentTextChanged.connect(self.update_view)
        self.chk_edges.toggled.connect(self.update_view)
        self.chk_shield_transparent.toggled.connect(self.update_view)
        self.chk_overlay_text.toggled.connect(self.update_view)
        self.cmb_cmap.currentTextChanged.connect(self.update_view)
        self.edit_vmin.editingFinished.connect(self.update_view)
        self.edit_vmax.editingFinished.connect(self.update_view)
        self.btn_auto_range.clicked.connect(self.clear_range)
        self.btn_view_xp.clicked.connect(lambda: self.set_view_vector((1, 0, 0)))
        self.btn_view_xn.clicked.connect(lambda: self.set_view_vector((-1, 0, 0)))
        self.btn_view_yp.clicked.connect(lambda: self.set_view_vector((0, 1, 0)))
        self.btn_view_yn.clicked.connect(lambda: self.set_view_vector((0, -1, 0)))
        self.btn_view_zp.clicked.connect(lambda: self.set_view_vector((0, 0, 1)))
        self.btn_view_zn.clicked.connect(lambda: self.set_view_vector((0, 0, -1)))
        self.btn_view_iso_1.clicked.connect(lambda: self.set_view_vector((-1, -1, 1)))
        self.btn_view_iso_2.clicked.connect(lambda: self.set_view_vector((1, -1, -1)))
        self.btn_view_wind.clicked.connect(self.set_view_wind)
        self.btn_view_wind_rev.clicked.connect(self.set_view_wind_reverse)

    def logln(self, message: str) -> None:
        self.log_message.emit(message)

    def set_case_rows(self, rows: Sequence[CaseRow] | None) -> None:
        self._case_rows = () if rows is None else tuple(rows)

    @QtCore.Slot()
    def clear_view(self) -> None:
        self._poly = None
        self._loaded_vtp_path = None
        self._display_case_row = None
        self._scalar_fields = {}
        self._overlay_actor = None
        self._camera_initialized = False
        self.cmb_scalar.clear()
        try:
            self.plotter.clear()
            self.plotter.render()
        except Exception:
            pass

    def clear_range(self) -> None:
        self.edit_vmin.clear()
        self.edit_vmax.clear()
        self.update_view()

    def open_vtp(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open VTP",
            str(self.default_artifact_dir()),
            "VTK PolyData (*.vtp)",
        )
        if path:
            self.load_vtp(path)

    def load_vtp(
        self,
        path: str,
        poly: object | None = None,
        case_row: CaseRow | None = None,
    ) -> bool:
        """Load and render a VTP; manual inspection does not require a match."""
        if poly is None:
            try:
                loaded = self._artifact_reader(path)
            except Exception as exc:
                self.clear_view()
                self.logln(f"[ERROR] Failed to read VTP: {exc}")
                return False
        else:
            loaded = poly
        try:
            fields = discover_scalar_fields(
                loaded.cell_data,
                n_cells=loaded.n_cells,
                preferred=self.spec.preferred_scalars,
            )
        except Exception as exc:
            self.clear_view()
            self.logln(f"[ERROR] Invalid VTP cell data: {exc}")
            return False

        self._loaded_vtp_path = Path(path).expanduser()
        self._poly = loaded
        if case_row is not None:
            self._display_case_row = dict(case_row)
        elif self.spec.adapters is not None:
            self._display_case_row = resolve_matching_case_row(
                loaded,
                self._case_rows,
                self.spec.adapters.build_case_signatures,
            )
        else:
            self._display_case_row = None
        self._set_scalar_fields(fields)
        self.logln(f"[VIEW] Loaded VTP: {path}")
        self.update_view()
        return True

    def _set_scalar_fields(self, fields: Sequence[ScalarField]) -> None:
        previous = self.cmb_scalar.currentText()
        self._scalar_fields = {field.name: field for field in fields}
        blocker = QtCore.QSignalBlocker(self.cmb_scalar)
        self.cmb_scalar.clear()
        self.cmb_scalar.addItems(list(self._scalar_fields))
        if previous in self._scalar_fields:
            self.cmb_scalar.setCurrentText(previous)
        del blocker

    def default_artifact_dir(self) -> Path:
        if self._loaded_vtp_path is not None:
            return self._loaded_vtp_path.parent
        if self._display_case_row is not None:
            value = str(self._display_case_row.get("out_dir", "")).strip()
            if value:
                return Path(value).expanduser()
        return Path.cwd()

    def set_view_vector(self, vector: tuple[float, float, float]) -> None:
        self.plotter.view_vector(vector)
        self.plotter.render()

    def _current_velocity_hat(self) -> np.ndarray | None:
        if self._display_case_row is None or self.spec.adapters is None:
            return None
        try:
            vector = np.asarray(
                self.spec.adapters.resolve_velocity_hat_stl(self._display_case_row),
                dtype=np.float64,
            )
        except Exception:
            return None
        if vector.shape != (3,) or not np.isfinite(vector).all():
            return None
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return None
        return vector / norm

    def set_view_wind(self) -> None:
        velocity = self._current_velocity_hat()
        if velocity is None:
            self.logln("[WARN] Wind view is unavailable for the displayed VTP.")
            return
        self.set_view_vector(tuple((-velocity).tolist()))

    def set_view_wind_reverse(self) -> None:
        velocity = self._current_velocity_hat()
        if velocity is None:
            self.logln("[WARN] Reverse-wind view is unavailable for the displayed VTP.")
            return
        self.set_view_vector(tuple(velocity.tolist()))

    def _automatic_limits(self, scalar: str) -> tuple[float, float] | None:
        if self._poly is None or scalar not in self._scalar_fields:
            return None
        try:
            automatic = scalar_color_limits(
                self._scalar_fields[scalar],
                self._poly.cell_data[scalar],
            )
        except Exception:
            return None
        minimum_text = self.edit_vmin.text().strip()
        maximum_text = self.edit_vmax.text().strip()
        try:
            minimum = float(minimum_text) if minimum_text else automatic[0]
            maximum = float(maximum_text) if maximum_text else automatic[1]
        except ValueError:
            return automatic
        if not np.isfinite((minimum, maximum)).all():
            return automatic
        if minimum == maximum:
            maximum = minimum + 1.0e-12
        return (minimum, maximum)

    def _update_overlay(self) -> None:
        if self._overlay_actor is not None:
            try:
                self.plotter.remove_actor(self._overlay_actor)
            except Exception:
                pass
            self._overlay_actor = None
        if not self.chk_overlay_text.isChecked():
            return
        if self._display_case_row is not None:
            text = self.spec.format_case(self._display_case_row)
        elif self._poly is not None:
            case_id = field_data_scalar(self._poly, "case_id")
            text = f"case_id={case_id}" if case_id else ""
        else:
            text = ""
        if not text:
            text = "(no case info for displayed VTP)"
        self._overlay_actor = self.plotter.add_text(
            text,
            position="upper_left",
            font_size=10,
        )

    def _capture_camera_state(self) -> dict[str, object] | None:
        try:
            camera = self.plotter.camera
            return {
                "position": tuple(camera.position),
                "focal_point": tuple(camera.focal_point),
                "up": tuple(camera.up),
                "clipping_range": tuple(camera.clipping_range),
                "parallel_projection": bool(camera.parallel_projection),
                "parallel_scale": float(camera.parallel_scale),
            }
        except Exception:
            return None

    def _restore_camera_state(self, state: dict[str, object] | None) -> bool:
        if state is None:
            return False
        try:
            camera = self.plotter.camera
            for name, value in state.items():
                setattr(camera, name, value)
            return True
        except Exception:
            return False

    @QtCore.Slot()
    def update_view(self) -> None:
        if self._poly is None:
            return
        previous_camera = (
            self._capture_camera_state() if self._camera_initialized else None
        )
        self.plotter.clear()
        scalar = self.cmb_scalar.currentText()
        scalar_name = scalar if scalar in self._scalar_fields else None
        common = {
            "scalars": scalar_name,
            "cmap": self.cmb_cmap.currentText(),
            "clim": self._automatic_limits(scalar),
            "show_edges": self.chk_edges.isChecked(),
        }
        shield = self._shield_mask()
        if shield is None:
            self.plotter.add_mesh(self._poly, opacity=1.0, **common)
        else:
            self._add_shield_groups(shield, common)
        self._update_overlay()
        self.plotter.add_axes()
        if not self._restore_camera_state(previous_camera):
            self.plotter.reset_camera()
            self.plotter.view_vector(self._default_view_vec)
        self._camera_initialized = True
        self.plotter.render()

    def _shield_mask(self) -> np.ndarray | None:
        if self._poly is None:
            return None
        try:
            values = np.asarray(self._poly.cell_data["shielded"])
        except Exception:
            return None
        if values.shape != (self._poly.n_cells,):
            return None
        return values.astype(bool)

    def _add_shield_groups(self, shield: np.ndarray, common: dict[str, object]) -> None:
        for masked, opacity in (
            (False, 1.0),
            (True, 0.30 if self.chk_shield_transparent.isChecked() else 1.0),
        ):
            indices = np.flatnonzero(shield == masked)
            if indices.size == 0:
                continue
            subset = self._poly.extract_cells(indices)
            self.plotter.add_mesh(subset, opacity=opacity, **common)


__all__ = ("ViewerPanel",)
