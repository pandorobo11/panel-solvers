"""Thin FMF policy for the shared case-table reader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from panelsolver.app.case_io import (
    AddIssue,
    CaseReaderPolicy,
    InputValidationError,
    ValidationIssue,
    read_case_table,
)
from panelsolver.models.sentman_atmosphere import altitude_range_km

REQUIRED = (
    "case_id",
    "stl_path",
    "stl_scale_m_per_unit",
    "alpha_deg",
    "beta_or_bank_deg",
    "Tw_K",
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
    "S",
    "Ti_K",
    "Mach",
    "Altitude_km",
    "Tw_K",
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
    "alpha_deg",
    "beta_or_bank_deg",
    "Tw_K",
    "ref_x_m",
    "ref_y_m",
    "ref_z_m",
    "Aref_m2",
    "Lref_Cl_m",
    "Lref_Cm_m",
    "Lref_Cn_m",
)
NUMERIC_OPTIONAL = ("S", "Ti_K", "Mach", "Altitude_km")
POSITIVE_COLUMNS = frozenset(
    {
        "stl_scale_m_per_unit",
        "Tw_K",
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
    "out_dir": "outputs",
}
def _validate_rows(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    mode_a_s = frame["S"].notna()
    mode_a_ti = frame["Ti_K"].notna()
    mode_b_mach = frame["Mach"].notna()
    mode_b_altitude = frame["Altitude_km"].notna()
    for index in frame.index[mode_a_s ^ mode_a_ti]:
        add_issue(int(index), "S,Ti_K", "Mode A requires both 'S' and 'Ti_K'.")
    for index in frame.index[mode_b_mach ^ mode_b_altitude]:
        add_issue(
            int(index),
            "Mach,Altitude_km",
            "Mode B requires both 'Mach' and 'Altitude_km'.",
        )
    mode_a = mode_a_s & mode_a_ti
    mode_b = mode_b_mach & mode_b_altitude
    for index in frame.index[mode_a & mode_b]:
        add_issue(int(index), "mode", "Specify either Mode A or Mode B, not both.")
    for index in frame.index[(~mode_a) & (~mode_b)]:
        add_issue(
            int(index),
            "mode",
            "Specify one complete mode "
            "(Mode A: S+Ti_K, Mode B: Mach+Altitude_km).",
        )
    for column in ("S", "Ti_K", "Mach"):
        for index in frame.index[frame[column].notna() & (frame[column] <= 0.0)]:
            add_issue(int(index), column, "must be > 0 when specified.")
    minimum, maximum = altitude_range_km()
    finite = frame["Altitude_km"].notna() & np.isfinite(frame["Altitude_km"])
    invalid = finite & (
        (frame["Altitude_km"] < minimum) | (frame["Altitude_km"] > maximum)
    )
    for index in frame.index[invalid]:
        add_issue(
            int(index),
            "Altitude_km",
            f"must be within [{minimum}, {maximum}] km.",
        )


CASE_READER_POLICY = CaseReaderPolicy(
    required_columns=REQUIRED,
    input_columns=INPUT_COLUMN_ORDER,
    numeric_required=NUMERIC_REQUIRED,
    numeric_optional=NUMERIC_OPTIONAL,
    positive_columns=POSITIVE_COLUMNS,
    defaults=DEFAULTS,
    validate_rows=_validate_rows,
    required_numeric_message_style="split",
    keep_default_na=True,
    fill_defaults_by_presence=False,
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
