"""Shared case loading, table selection, and automatic artifact matching."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import pyvista as pv
from PySide6 import QtCore, QtWidgets

from .solver_spec import CaseRow, SolverSpec
from .viewer_data import match_artifact_case


def _issue_value(issue: object, name: str) -> object | None:
    if isinstance(issue, Mapping):
        return issue.get(name)
    return getattr(issue, name, None)


class ValidationIssuesDialog(QtWidgets.QDialog):
    """Product-neutral tabular rendering of structured validation issues."""

    def __init__(self, file_path: str, issues: Sequence[object], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Input Validation Errors")
        self.resize(980, 420)
        self._issues = tuple(issues)
        layout = QtWidgets.QVBoxLayout(self)
        summary = QtWidgets.QLabel(
            f"Failed to load input file:\n{file_path}\n\n"
            f"Validation issues: {len(self._issues)}"
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)
        self.table = QtWidgets.QTableWidget(len(self._issues), 4)
        self.table.setHorizontalHeaderLabels(["Row", "Case ID", "Field", "Message"])
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        for row_index, issue in enumerate(self._issues):
            values = (
                _issue_value(issue, "row_number"),
                _issue_value(issue, "case_id"),
                _issue_value(issue, "field"),
                _issue_value(issue, "message"),
            )
            for column, value in enumerate(values):
                text = "" if value is None else str(value)
                self.table.setItem(row_index, column, QtWidgets.QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table, 1)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        copy_button = QtWidgets.QPushButton("Copy")
        close_button = QtWidgets.QPushButton("Close")
        buttons.addWidget(copy_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        copy_button.clicked.connect(self.copy_issues)
        close_button.clicked.connect(self.accept)

    def copy_issues(self) -> None:
        lines = ["row\tcase_id\tfield\tmessage"]
        for issue in self._issues:
            values = (
                _issue_value(issue, "row_number"),
                _issue_value(issue, "case_id"),
                _issue_value(issue, "field"),
                _issue_value(issue, "message"),
            )
            lines.append("\t".join("" if value is None else str(value) for value in values))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))


class CasesPanel(QtWidgets.QWidget):
    """Load product-adapted rows and coordinate selection with the viewer."""

    vtp_loaded = QtCore.Signal(str, object, object)
    viewer_clear_requested = QtCore.Signal()
    cases_updated = QtCore.Signal(object)
    run_requested = QtCore.Signal(object, int, object)

    def __init__(
        self,
        spec: SolverSpec,
        parent=None,
        *,
        artifact_reader=pv.read,
    ) -> None:
        if not isinstance(spec, SolverSpec):
            raise TypeError("spec must be a SolverSpec")
        if spec.adapters is None:
            raise ValueError("spec.adapters is required by CasesPanel")
        if not callable(artifact_reader):
            raise TypeError("artifact_reader must be callable")
        super().__init__(parent)
        self.spec = spec
        self._artifact_reader = artifact_reader
        self.case_rows: tuple[CaseRow, ...] = ()
        self.input_path: Path | None = None
        self._table_columns: tuple[str, ...] = ()

        self.input_value = QtWidgets.QLineEdit()
        self.input_value.setReadOnly(True)
        self.input_value.setPlaceholderText("CSV / Excel input file")
        self.btn_pick_input = QtWidgets.QPushButton("Select Input File")
        self.btn_run = QtWidgets.QPushButton("Run Selected Cases")
        self.btn_run.setEnabled(False)
        self.lbl_case_summary = QtWidgets.QLabel("No cases loaded")
        self.lbl_selection_summary = QtWidgets.QLabel("Selected: 0")
        self.spin_workers = QtWidgets.QSpinBox()
        self.spin_workers.setRange(1, os.cpu_count() or 1)
        self.spin_workers.setValue(1)
        self.case_table = QtWidgets.QTableWidget()
        self.case_table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.case_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.case_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.case_table.setAlternatingRowColors(True)
        self.case_table.setWordWrap(False)
        self.case_table.verticalHeader().setVisible(False)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(8000)
        self.log.setMinimumHeight(180)
        self._build_layout()

        self.btn_pick_input.clicked.connect(self.pick_input_file)
        self.btn_run.clicked.connect(self.request_run)
        self.case_table.itemSelectionChanged.connect(self.on_case_selection_changed)

    def _build_layout(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        input_row = QtWidgets.QHBoxLayout()
        input_row.addWidget(self.input_value, 1)
        input_row.addWidget(self.btn_pick_input)
        layout.addLayout(input_row)
        summaries = QtWidgets.QHBoxLayout()
        summaries.addWidget(self.lbl_case_summary)
        summaries.addStretch(1)
        summaries.addWidget(self.lbl_selection_summary)
        layout.addLayout(summaries)
        layout.addWidget(self.case_table, 4)
        run_row = QtWidgets.QHBoxLayout()
        run_row.addWidget(QtWidgets.QLabel("Workers:"))
        run_row.addWidget(self.spin_workers)
        run_row.addStretch(1)
        run_row.addWidget(self.btn_run)
        layout.addLayout(run_row)
        layout.addWidget(self.log, 2)

    def logln(self, message: str) -> None:
        self.log.appendPlainText(message)

    def pick_input_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            str(Path.cwd()),
            "CSV/Excel (*.csv *.xlsx *.xlsm *.xls)",
        )
        if path:
            self.load_input_file(path)

    def load_input_file(self, path: str | Path) -> bool:
        """Read cases through the selected product adapter and reset on failure."""
        try:
            raw_rows = self.spec.adapters.read_cases(path)
            rows = tuple(raw_rows)
            if not rows:
                raise ValueError("Input contains no cases.")
            if any(not isinstance(row, Mapping) for row in rows):
                raise TypeError("read_cases must return mappings")
            normalized = tuple(dict(row) for row in rows)
        except Exception as exc:
            self.clear_loaded_cases()
            issues = getattr(exc, "issues", None)
            if issues is not None:
                issue_list = tuple(issues)
                self.logln(f"[ERROR] Invalid input file: {len(issue_list)} issue(s).")
                ValidationIssuesDialog(str(path), issue_list, self).exec()
            else:
                self.logln(f"[ERROR] Failed to read input file: {exc}")
                QtWidgets.QMessageBox.critical(
                    self,
                    "Input Read Error",
                    f"Failed to read input file:\n{path}\n\n{exc}",
                )
            return False

        self.input_path = Path(path).expanduser()
        self.input_value.setText(str(path))
        self.case_rows = normalized
        self._populate_case_table()
        self.btn_run.setEnabled(True)
        self.logln(f"[OK] Loaded {len(self.case_rows)} case(s). Select and run.")
        self.cases_updated.emit(self.case_rows)
        return True

    def _ordered_columns(self) -> tuple[str, ...]:
        extras: list[str] = []
        known = set(self.spec.case_columns)
        for row in self.case_rows:
            for name in row:
                if name not in known and name not in extras:
                    extras.append(name)
        return (*self.spec.case_columns, *extras)

    def _populate_case_table(self) -> None:
        self._table_columns = self._ordered_columns()
        self.case_table.clear()
        self.case_table.setColumnCount(len(self._table_columns))
        self.case_table.setRowCount(len(self.case_rows))
        headers = [
            "stl_name" if name == "stl_path" else name
            for name in self._table_columns
        ]
        self.case_table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(self.case_rows):
            for column, name in enumerate(self._table_columns):
                value = row.get(name)
                text = "" if value is None else str(value)
                display = self.format_stl_name(text) if name == "stl_path" else text
                item = QtWidgets.QTableWidgetItem(display)
                if name == "stl_path" and text:
                    item.setToolTip(text)
                if column == 0:
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, row_index)
                self.case_table.setItem(row_index, column, item)
        self.case_table.resizeColumnsToContents()
        if "stl_path" in self._table_columns:
            self.case_table.setColumnWidth(self._table_columns.index("stl_path"), 220)
        self._refresh_summary()

    @staticmethod
    def format_stl_name(value: str) -> str:
        paths = [part.strip() for part in value.split(";") if part.strip()]
        return ", ".join(Path(path).name for path in paths)

    def selected_case_rows(self) -> list[CaseRow]:
        selection = self.case_table.selectionModel().selectedRows()
        indices = sorted(
            {
                int(item.data(QtCore.Qt.ItemDataRole.UserRole))
                for model_index in selection
                if (item := self.case_table.item(model_index.row(), 0)) is not None
                and item.data(QtCore.Qt.ItemDataRole.UserRole) is not None
            }
        )
        return [self.case_rows[index] for index in indices]

    def selected_or_all_case_rows(self) -> list[CaseRow]:
        selected = self.selected_case_rows()
        return selected if selected else list(self.case_rows)

    def on_case_selection_changed(self) -> None:
        self._refresh_summary()
        selected = self.selected_case_rows()
        if not selected:
            self.viewer_clear_requested.emit()
            return
        self._auto_load_case_artifact(selected[0])

    def _auto_load_case_artifact(self, row: CaseRow) -> None:
        case_id = str(row.get("case_id", "")).strip()
        raw_out_dir = str(row.get("out_dir", "")).strip() or "outputs"
        if not case_id:
            self.viewer_clear_requested.emit()
            return
        path = Path(raw_out_dir).expanduser() / f"{case_id}.vtp"
        if not path.exists():
            self.viewer_clear_requested.emit()
            return
        try:
            artifact = self._artifact_reader(str(path))
        except Exception as exc:
            self.viewer_clear_requested.emit()
            self.logln(f"[ERROR] Failed to read VTP: {exc}")
            return
        candidates = self.spec.adapters.build_case_signatures(row)
        if match_artifact_case(artifact, row, candidates).matched:
            self.vtp_loaded.emit(str(path), artifact, row)
        else:
            self.viewer_clear_requested.emit()

    def request_run(self) -> None:
        if self.input_path is None or not self.case_rows:
            return
        rows = self.selected_or_all_case_rows()
        output_dir = self.input_path.parent / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        default_path = output_dir / f"{self.input_path.stem}_result.csv"
        selected_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Results",
            str(default_path),
            "CSV (*.csv)",
        )
        if not selected_path:
            self.logln("[SKIP] Result output canceled.")
            return
        try:
            output_path = self.spec.adapters.validate_output_path(
                selected_path,
                self.input_path,
                rows,
            )
        except Exception as exc:
            self.logln(f"[ERROR] {exc}")
            QtWidgets.QMessageBox.critical(
                self,
                "Invalid Output Path",
                str(exc),
            )
            return
        self.run_requested.emit(rows, int(self.spin_workers.value()), output_path)

    def clear_loaded_cases(self) -> None:
        self.case_rows = ()
        self.input_path = None
        self._table_columns = ()
        self.input_value.clear()
        self.case_table.clear()
        self.case_table.setRowCount(0)
        self.case_table.setColumnCount(0)
        self.btn_run.setEnabled(False)
        self.viewer_clear_requested.emit()
        self.cases_updated.emit(self.case_rows)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        total = len(self.case_rows)
        selected = len(self.case_table.selectionModel().selectedRows())
        self.lbl_case_summary.setText(
            "No cases loaded" if total == 0 else f"Loaded: {total} case(s)"
        )
        self.lbl_selection_summary.setText(f"Selected: {selected}")


__all__ = ("CasesPanel", "ValidationIssuesDialog")
