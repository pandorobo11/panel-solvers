"""Thin newtsolver policy for the shared case-table reader."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from panelsolver.app.case_io import (
    AddIssue,
    CaseReaderPolicy,
    InputValidationError,
    ValidationIssue,
    count_semicolon_entries,
    expand_component_values,
    read_case_table,
    split_semicolon_tokens,
)
from panelsolver.models.hypersonic.selectors import (
    normalize_leeward_equation,
    normalize_windward_equation,
)

REQUIRED = (
    "case_id",
    "stl_path",
    "stl_scale_m_per_unit",
    "Mach",
    "gamma",
    "alpha_deg",
    "beta_or_bank_deg",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
)
INPUT_COLUMN_ORDER = (
    "case_id",
    "stl_path",
    "stl_scale_m_per_unit",
    "Mach",
    "gamma",
    "windward_eq",
    "leeward_eq",
    "alpha_deg",
    "beta_or_bank_deg",
    "attitude_input",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
    "shielding_on",
    "ray_backend",
    "out_dir",
    "save_vtp_on",
    "save_npz_on",
)
NUMERIC_REQUIRED = (
    "stl_scale_m_per_unit",
    "Mach",
    "gamma",
    "alpha_deg",
    "beta_or_bank_deg",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
)
POSITIVE_COLUMNS = frozenset(
    {
        "stl_scale_m_per_unit",
        "Mach",
        "gamma",
        "Aref_m2",
        "Lref_Cl_m",
        "Lref_Cm_m",
        "Lref_Cn_m",
    }
)
DEFAULTS = {
    "shielding_on": 0,
    "save_vtp_on": 1,
    "save_npz_on": 0,
    "ray_backend": "auto",
    "attitude_input": "beta_tan",
    "windward_eq": "newtonian",
    "leeward_eq": "shield",
    "out_dir": "outputs",
}
_CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _validate_case_id(value: object) -> str:
    case_id = "" if value is None else str(value).strip()
    if not case_id:
        raise ValueError("must not be blank.")
    if _CASE_ID_PATTERN.fullmatch(case_id) is None:
        raise ValueError(
            "must start with an ASCII letter or digit and contain only "
            "ASCII letters, digits, '.', '_' or '-'."
        )
    if case_id in {".", ".."} or case_id.endswith((".", " ")):
        raise ValueError("is not a portable filename.")
    if case_id.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        raise ValueError("is a reserved filename on Windows.")
    return case_id


def _validate_case_ids(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    frame["case_id"] = (
        frame["case_id"].where(frame["case_id"].notna(), "").astype(str).str.strip()
    )
    valid_ids: list[str] = []
    for index, value in frame["case_id"].items():
        try:
            valid_ids.append(_validate_case_id(value))
        except ValueError as exc:
            valid_ids.append(str(value))
            add_issue(int(index), "case_id", str(exc))
    duplicate_keys = pd.Series(valid_ids, index=frame.index).str.casefold()
    duplicate_ids = sorted(
        frame.loc[duplicate_keys.duplicated(keep=False), "case_id"].unique()
    )
    if duplicate_ids:
        add_issue(
            None,
            "case_id",
            "Duplicate case_id values are not allowed (case-insensitive): "
            f"{duplicate_ids}",
        )


def _validate_surface_equations(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    for index in frame.index:
        component_count = max(count_semicolon_entries(frame.at[index, "stl_path"]), 1)
        try:
            _, canonical = expand_component_values(
                frame.at[index, "windward_eq"],
                default_value="newtonian",
                resolver=normalize_windward_equation,
                component_count=component_count,
                field_name="windward_eq",
            )
            frame.at[index, "windward_eq"] = canonical
        except ValueError as exc:
            add_issue(int(index), "windward_eq", str(exc))
            continue
        try:
            _, canonical = expand_component_values(
                frame.at[index, "leeward_eq"],
                default_value="shield",
                resolver=normalize_leeward_equation,
                component_count=component_count,
                field_name="leeward_eq",
            )
            frame.at[index, "leeward_eq"] = canonical
        except ValueError as exc:
            add_issue(int(index), "leeward_eq", str(exc))


def _validate_rows(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    _validate_surface_equations(frame, add_issue)
    for index in frame.index[frame["gamma"] <= 1.0]:
        add_issue(int(index), "gamma", "must be > 1.")
    for index in frame.index[frame["Mach"] <= 1.0]:
        windward = {
            token
            for token in split_semicolon_tokens(frame.at[index, "windward_eq"])
            if token
        }
        for equation in (
            "modified_newtonian",
            "tangent_wedge",
            "tangent_cone",
        ):
            if equation in windward:
                add_issue(
                    int(index),
                    "Mach",
                    f"must be > 1 when windward_eq={equation}.",
                )
        if "prandtl_meyer" in {
            token
            for token in split_semicolon_tokens(frame.at[index, "leeward_eq"])
            if token
        }:
            add_issue(
                int(index),
                "Mach",
                "must be > 1 when leeward_eq=prandtl_meyer.",
            )


def _no_attitude_domain_check(_frame: pd.DataFrame, _add_issue: AddIssue) -> None:
    return None


CASE_READER_POLICY = CaseReaderPolicy(
    required_columns=REQUIRED,
    input_columns=INPUT_COLUMN_ORDER,
    numeric_required=NUMERIC_REQUIRED,
    numeric_optional=(),
    positive_columns=POSITIVE_COLUMNS,
    defaults=DEFAULTS,
    validate_case_ids=_validate_case_ids,
    validate_rows=_validate_rows,
    validate_attitude_domain=_no_attitude_domain_check,
    required_numeric_message_style="finite",
    keep_default_na=False,
    fill_defaults_by_presence=True,
    xls_engine="openpyxl",
    excel_case_id_dtype="string",
)


def read_cases(path: str | Path) -> pd.DataFrame:
    return read_case_table(path, CASE_READER_POLICY)


__all__ = (
    "CASE_READER_POLICY",
    "DEFAULTS",
    "INPUT_COLUMN_ORDER",
    "InputValidationError",
    "ValidationIssue",
    "read_cases",
)
