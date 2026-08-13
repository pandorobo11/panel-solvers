"""Shared case-table mechanics with explicit product validation policies."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .attitude import ATTITUDE_INPUT_VALUES

type AddIssue = Callable[[int | None, str | None, str], None]
type DataFrameValidator = Callable[[pd.DataFrame, AddIssue], None]

FLAG_COLUMNS = ("shielding_on", "save_vtp_on", "save_npz_on")
RAY_BACKEND_VALUES = frozenset({"auto", "rtree", "embree"})
_INVALID_CASE_ID_CHARS = frozenset('/\\<>:"|?*')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def is_filled(value: object) -> bool:
    """Return whether a table-like cell is specified under the pinned rules."""
    if value is None:
        return False
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return False
    return str(value).strip() != ""


def _is_numeric_boolean(value: object) -> bool:
    return isinstance(value, (bool, np.bool_))


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One structured validation error for an input case table."""

    row_number: int | None
    case_id: str | None
    field: str | None
    message: str


class InputValidationError(ValueError):
    """Raised when one or more product-selected table checks fail."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        lines = ["Invalid input table:"]
        for issue in self.issues:
            parts: list[str] = []
            if issue.row_number is not None:
                parts.append(f"row {issue.row_number}")
            if issue.case_id:
                parts.append(f"case_id='{issue.case_id}'")
            if issue.field:
                parts.append(issue.field)
            prefix = ", ".join(parts)
            lines.append(
                f"- {prefix}: {issue.message}" if prefix else f"- {issue.message}"
            )
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class CaseReaderPolicy:
    """Product-owned schema and validation callbacks for shared table I/O."""

    required_columns: tuple[str, ...]
    input_columns: tuple[str, ...]
    numeric_required: tuple[str, ...]
    numeric_optional: tuple[str, ...]
    positive_columns: frozenset[str]
    defaults: Mapping[str, object]
    validate_rows: DataFrameValidator
    required_numeric_message_style: str
    keep_default_na: bool
    fill_defaults_by_presence: bool

    def __post_init__(self) -> None:
        for field_name in ("validate_rows",):
            if not callable(getattr(self, field_name)):
                raise TypeError(f"CaseReaderPolicy.{field_name} must be callable")
        if self.required_numeric_message_style not in {"split", "finite"}:
            raise ValueError(
                "required_numeric_message_style must be 'split' or 'finite'"
            )


def validate_case_id(value: object) -> str:
    """Return one portable Unicode case identifier or raise ``ValueError``."""
    case_id = unicodedata.normalize("NFC", "" if value is None else str(value))
    if not case_id:
        raise ValueError("must not be empty.")
    if case_id in {".", ".."}:
        raise ValueError("must not be '.' or '..'.")
    if case_id.endswith((".", " ")):
        raise ValueError("must not end with a dot or space.")
    if any(
        char in _INVALID_CASE_ID_CHARS or unicodedata.category(char) == "Cc"
        for char in case_id
    ):
        raise ValueError(
            "must be a portable filename without path separators, control "
            "characters, or Windows-invalid characters."
        )
    reserved_stem = case_id.split(".", 1)[0].rstrip(" ").upper()
    if reserved_stem in _WINDOWS_RESERVED_NAMES:
        raise ValueError("is a reserved filename on Windows.")
    return case_id


def _validate_case_ids(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    frame["case_id"] = frame["case_id"].where(frame["case_id"].notna(), "").astype(str)
    valid_ids: list[str] = []
    for index, value in frame["case_id"].items():
        try:
            valid_ids.append(validate_case_id(value))
        except ValueError as exc:
            valid_ids.append(unicodedata.normalize("NFC", str(value)))
            add_issue(int(index), "case_id", str(exc))
    frame["case_id"] = pd.Series(valid_ids, index=frame.index)
    duplicate_keys = frame["case_id"].map(
        lambda case_id: unicodedata.normalize("NFC", case_id.casefold())
    )
    duplicate_ids = sorted(
        frame.loc[duplicate_keys.duplicated(keep=False), "case_id"].unique()
    )
    if duplicate_ids:
        add_issue(
            None,
            "case_id",
            "Duplicate case_id values are not allowed after Unicode casefold: "
            f"{duplicate_ids}",
        )


def count_semicolon_entries(value: object) -> int:
    return len([part for part in split_semicolon_tokens(value) if part])


def split_semicolon_tokens(value: object) -> list[str]:
    raw = str(value or "").strip()
    return [] if not raw else [part.strip() for part in raw.split(";")]


def expand_component_values(
    raw_value: object,
    *,
    default_value: str,
    resolver: Callable[[object], str],
    component_count: int,
    field_name: str,
) -> tuple[list[str], str]:
    """Preserve one-or-per-STL selector expansion and error wording."""
    tokens = split_semicolon_tokens(raw_value)
    if not tokens:
        tokens = [default_value]
    elif any(token == "" for token in tokens):
        raise ValueError(f"{field_name} must not contain empty ';' entries.")
    if len(tokens) == 1:
        resolved = resolver(tokens[0])
        return [resolved] * component_count, resolved
    if len(tokens) != component_count:
        raise ValueError(
            f"{field_name} must have 1 entry or {component_count} entries "
            f"(to match stl_path), got {len(tokens)}."
        )
    values = [resolver(token) for token in tokens]
    return values, ";".join(values)


def _validate_and_resolve_stl_paths(
    frame: pd.DataFrame,
    input_path: Path,
    add_issue: AddIssue,
) -> None:
    base_dir = input_path.parent
    for index, raw in frame["stl_path"].items():
        if not is_filled(raw):
            add_issue(int(index), "stl_path", "is required.")
            continue
        paths = [part.strip() for part in str(raw).split(";") if part.strip()]
        if not paths:
            add_issue(int(index), "stl_path", "has no valid entry.")
            continue
        resolved_paths: list[str] = []
        for raw_path in paths:
            candidate = Path(raw_path).expanduser()
            resolved: Path | None = None
            if candidate.is_absolute() and candidate.exists():
                resolved = candidate.resolve()
            elif not candidate.is_absolute() and (base_dir / candidate).exists():
                resolved = (base_dir / candidate).resolve()
            else:
                add_issue(
                    int(index),
                    "stl_path",
                    f"STL file not found: '{raw_path}' "
                    f"(checked relative to '{base_dir}').",
                )
            if resolved is not None:
                resolved_paths.append(str(resolved))
        if resolved_paths:
            frame.at[index, "stl_path"] = ";".join(resolved_paths)


def _validate_required_numeric(
    frame: pd.DataFrame,
    policy: CaseReaderPolicy,
    add_issue: AddIssue,
) -> None:
    for column in policy.numeric_required:
        boolean = frame[column].map(_is_numeric_boolean)
        parsed = pd.to_numeric(frame[column].where(~boolean), errors="coerce")
        invalid = boolean | parsed.isna()
        nonfinite = (~invalid) & (~np.isfinite(parsed))
        if policy.required_numeric_message_style == "finite":
            for index in frame.index[invalid | nonfinite]:
                add_issue(int(index), column, "must be a finite numeric value.")
        else:
            for index in frame.index[invalid]:
                add_issue(int(index), column, "must be numeric.")
            for index in frame.index[nonfinite]:
                add_issue(int(index), column, "must be finite.")
        frame[column] = parsed


def _validate_optional_numeric(
    frame: pd.DataFrame,
    policy: CaseReaderPolicy,
    add_issue: AddIssue,
) -> None:
    for column in policy.numeric_optional:
        if column not in frame.columns:
            frame[column] = float("nan")
        filled = frame[column].map(is_filled)
        boolean = frame[column].map(_is_numeric_boolean)
        parsed = pd.to_numeric(
            frame[column].where(filled & ~boolean), errors="coerce"
        )
        invalid = filled & (boolean | parsed.isna())
        nonfinite = parsed.notna() & (~np.isfinite(parsed))
        for index in frame.index[invalid]:
            add_issue(int(index), column, "must be numeric when specified.")
        for index in frame.index[nonfinite]:
            add_issue(int(index), column, "must be finite when specified.")
        frame[column] = parsed


def _validate_positive_columns(
    frame: pd.DataFrame,
    policy: CaseReaderPolicy,
    add_issue: AddIssue,
) -> None:
    for column in policy.positive_columns:
        invalid = frame[column] <= 0.0
        for index in frame.index[invalid]:
            add_issue(int(index), column, "must be > 0.")


def _validate_flags(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    for column in FLAG_COLUMNS:
        parsed = pd.to_numeric(frame[column], errors="coerce")
        invalid_numeric = parsed.isna()
        invalid_value = (~invalid_numeric) & (~parsed.isin([0, 1]))
        for index in frame.index[invalid_numeric]:
            add_issue(int(index), column, "must be 0 or 1.")
        for index in frame.index[invalid_value]:
            add_issue(int(index), column, "must be 0 or 1.")
        frame[column] = parsed.fillna(0).astype(int)


def _validate_ray_backend(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    frame["ray_backend"] = (
        frame["ray_backend"]
        .where(frame["ray_backend"].notna(), "auto")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    frame.loc[frame["ray_backend"] == "", "ray_backend"] = "auto"
    invalid = ~frame["ray_backend"].isin(RAY_BACKEND_VALUES)
    for index in frame.index[invalid]:
        add_issue(
            int(index),
            "ray_backend",
            "must be one of: auto, rtree, embree.",
        )


def _normalize_attitude(value: object) -> str:
    return str(value or "").strip().lower() or "beta_tan"


def _validate_attitude(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    frame["attitude_input"] = frame["attitude_input"].map(_normalize_attitude)
    invalid = ~frame["attitude_input"].isin(ATTITUDE_INPUT_VALUES)
    for index in frame.index[invalid]:
        add_issue(
            int(index),
            "attitude_input",
            "must be one of: beta_tan, beta_sin, bank.",
        )


def _validate_attitude_domain(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    beta_tan = frame["attitude_input"] == "beta_tan"
    beta_sin = frame["attitude_input"] == "beta_sin"
    invalid_alpha = (beta_tan | beta_sin) & (frame["alpha_deg"].abs() >= 90.0)
    invalid_beta = beta_tan & (frame["beta_or_bank_deg"].abs() >= 90.0)
    for index in frame.index[invalid_alpha]:
        add_issue(
            int(index),
            "alpha_deg",
            "must satisfy abs(alpha_deg) < 90 for beta_tan or beta_sin.",
        )
    for index in frame.index[invalid_beta]:
        add_issue(
            int(index),
            "beta_or_bank_deg",
            "must satisfy abs(beta_or_bank_deg) < 90 for beta_tan.",
        )


def _validate_out_dir(frame: pd.DataFrame, add_issue: AddIssue) -> None:
    frame["out_dir"] = frame["out_dir"].astype(str).str.strip()
    for index in frame.index[frame["out_dir"] == ""]:
        add_issue(int(index), "out_dir", "must not be blank.")


def _resolve_out_dirs(frame: pd.DataFrame, input_path: Path) -> None:
    for index, raw in frame["out_dir"].items():
        candidate = Path(str(raw)).expanduser()
        resolved = candidate.resolve() if candidate.is_absolute() else (
            input_path.parent / candidate
        ).resolve()
        frame.at[index, "out_dir"] = str(resolved)


def _validate_and_normalize(
    frame: pd.DataFrame,
    input_path: Path,
    policy: CaseReaderPolicy,
) -> pd.DataFrame:
    issues: list[ValidationIssue] = []

    def add_issue(index: int | None, field: str | None, message: str) -> None:
        row_number = None if index is None else int(index) + 2
        case_id = None
        if index is not None and "case_id" in frame.columns:
            text = str(frame.at[index, "case_id"]).strip()
            case_id = text or None
        issues.append(ValidationIssue(row_number, case_id, field, message))

    _validate_case_ids(frame, add_issue)
    _validate_and_resolve_stl_paths(frame, input_path, add_issue)
    _validate_required_numeric(frame, policy, add_issue)
    _validate_optional_numeric(frame, policy, add_issue)
    _validate_positive_columns(frame, policy, add_issue)
    policy.validate_rows(frame, add_issue)
    _validate_flags(frame, add_issue)
    _validate_ray_backend(frame, add_issue)
    _validate_attitude(frame, add_issue)
    _validate_attitude_domain(frame, add_issue)
    _validate_out_dir(frame, add_issue)
    if issues:
        raise InputValidationError(issues)
    _resolve_out_dirs(frame, input_path)
    return frame


def read_case_table(path: str | Path, policy: CaseReaderPolicy) -> pd.DataFrame:
    """Read and normalize one product case table through shared mechanics."""
    if not isinstance(policy, CaseReaderPolicy):
        raise TypeError("policy must be a CaseReaderPolicy")
    input_path = Path(path).expanduser()
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(
            input_path,
            dtype={"case_id": "string"},
            keep_default_na=policy.keep_default_na,
        )
    elif suffix in {".xlsx", ".xlsm", ".xls"}:
        engine = "xlrd" if suffix == ".xls" else "openpyxl"
        frame = pd.read_excel(
            input_path,
            engine=engine,
            dtype={"case_id": "string"},
            keep_default_na=policy.keep_default_na,
        )
    else:
        raise ValueError(f"Unsupported input format: {input_path.suffix}")

    missing = [
        column for column in policy.required_columns if column not in frame.columns
    ]
    if missing:
        raise InputValidationError(
            [
                ValidationIssue(
                    row_number=1,
                    case_id=None,
                    field="header",
                    message=f"Missing required columns: {missing}",
                )
            ]
        )

    for name, default in policy.defaults.items():
        if name not in frame.columns:
            frame[name] = default
        elif policy.fill_defaults_by_presence:
            frame[name] = frame[name].map(
                lambda value, default=default: value if is_filled(value) else default
            )
        else:
            frame[name] = frame[name].fillna(default)

    normalized = _validate_and_normalize(frame, input_path, policy)
    ordered = [name for name in policy.input_columns if name in normalized.columns]
    extras = [name for name in normalized.columns if name not in ordered]
    return normalized[ordered + extras]


__all__ = (
    "AddIssue",
    "CaseReaderPolicy",
    "InputValidationError",
    "ValidationIssue",
    "count_semicolon_entries",
    "expand_component_values",
    "is_filled",
    "read_case_table",
    "split_semicolon_tokens",
    "validate_case_id",
)
