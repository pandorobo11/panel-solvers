"""Thin newtsolver policy for the shared case-table reader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from panelsolver.app.case_io import (
    AddIssue,
    CaseReaderPolicy,
    InputValidationError,
    ValidationIssue,
    count_semicolon_entries,
    expand_component_values,
    normalize_optional_text,
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
    "ray_backend": "auto",
    "attitude_input": "beta_tan",
    "windward_eq": "newtonian",
    "leeward_eq": "shield",
    "out_dir": "outputs",
}


def _validate_surface_equations(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    for index in frame.index:
        component_count = max(count_semicolon_entries(frame.at[index, "stl_path"]), 1)
        try:
            windward = normalize_optional_text(
                frame.at[index, "windward_eq"],
                field="windward_eq",
                default="newtonian",
            )
            _, canonical = expand_component_values(
                windward,
                default_value="newtonian",
                resolver=normalize_windward_equation,
                component_count=component_count,
                field_name="windward_eq",
            )
            frame.at[index, "windward_eq"] = canonical
        except (TypeError, ValueError) as exc:
            add_issue(int(index), "windward_eq", str(exc))
            continue
        try:
            leeward = normalize_optional_text(
                frame.at[index, "leeward_eq"],
                field="leeward_eq",
                default="shield",
            )
            _, canonical = expand_component_values(
                leeward,
                default_value="shield",
                resolver=normalize_leeward_equation,
                component_count=component_count,
                field_name="leeward_eq",
            )
            frame.at[index, "leeward_eq"] = canonical
        except (TypeError, ValueError) as exc:
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


CASE_READER_POLICY = CaseReaderPolicy(
    required_columns=REQUIRED,
    input_columns=INPUT_COLUMN_ORDER,
    numeric_required=NUMERIC_REQUIRED,
    numeric_optional=(),
    positive_columns=POSITIVE_COLUMNS,
    defaults=DEFAULTS,
    validate_rows=_validate_rows,
    required_numeric_message_style="finite",
    keep_default_na=False,
    fill_defaults_by_presence=True,
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
