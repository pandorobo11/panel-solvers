"""Input-table-relative filesystem path policy for application artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

DEFAULT_OUTPUT_DIRECTORY = "outputs"


def absolute_input_path(input_path: str | Path) -> Path:
    """Make an input path absolute without following a file symlink."""
    source = Path(input_path).expanduser()
    return source if source.is_absolute() else Path.cwd() / source


def resolve_input_relative_path(
    path: str | Path,
    input_path: str | Path,
) -> Path:
    """Resolve ``path`` against the input table directory when it is relative."""
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    base_dir = absolute_input_path(input_path).parent
    return (base_dir / candidate).resolve(strict=False)


def resolve_case_output_dir(
    row: Mapping[str, object],
    input_path: str | Path,
) -> Path:
    """Return one case output directory under the shared input-relative policy."""
    raw = str(row.get("out_dir", "")).strip() or DEFAULT_OUTPUT_DIRECTORY
    return resolve_input_relative_path(raw, input_path)


def resolve_case_vtp_path(
    row: Mapping[str, object],
    input_path: str | Path,
) -> Path:
    """Return the planned VTP path for one case row."""
    case_id = str(row.get("case_id", "")).strip()
    return resolve_case_output_dir(row, input_path) / f"{case_id}.vtp"


def default_summary_output_path(input_path: str | Path) -> Path:
    """Return ``<input_dir>/outputs/<input_stem>_result.csv``."""
    source = absolute_input_path(input_path)
    return source.parent / DEFAULT_OUTPUT_DIRECTORY / f"{source.stem}_result.csv"


__all__ = (
    "DEFAULT_OUTPUT_DIRECTORY",
    "absolute_input_path",
    "default_summary_output_path",
    "resolve_case_output_dir",
    "resolve_case_vtp_path",
    "resolve_input_relative_path",
)
