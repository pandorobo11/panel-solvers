"""Policy-driven atomic CSV serialization for compatibility adapters."""

from __future__ import annotations

import csv
import os
import tempfile
import uuid
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TextIO

from panelsolver.core.csv_projection import CsvProjection
from panelsolver.core.errors import ContractValueError


class TempNameStyle(str, Enum):
    """Legacy same-directory temporary-file naming strategies."""

    NAMED_RANDOM = "named_random"
    UUID = "uuid"


@dataclass(frozen=True, slots=True)
class AtomicCsvWritePolicy:
    """Explicit temporary-file and durability behavior for one product."""

    temp_name_style: TempNameStyle
    fsync_before_replace: bool

    def __post_init__(self) -> None:
        if not isinstance(self.temp_name_style, TempNameStyle):
            raise ContractValueError(
                "AtomicCsvWritePolicy.temp_name_style",
                "must be a TempNameStyle",
            )
        if not isinstance(self.fsync_before_replace, bool):
            raise ContractValueError(
                "AtomicCsvWritePolicy.fsync_before_replace",
                "must be a boolean",
            )


DURABLE_CSV_WRITE_POLICY = AtomicCsvWritePolicy(
    temp_name_style=TempNameStyle.NAMED_RANDOM,
    fsync_before_replace=True,
)


def write_csv_atomic(
    out_path: str | Path,
    projection: CsvProjection,
    policy: AtomicCsvWritePolicy,
) -> None:
    """Write a complete semantic CSV snapshot using the selected legacy policy."""
    if not isinstance(projection, CsvProjection):
        raise ContractValueError("write_csv_atomic.projection", "must be CsvProjection")
    if not isinstance(policy, AtomicCsvWritePolicy):
        raise ContractValueError(
            "write_csv_atomic.policy",
            "must be AtomicCsvWritePolicy",
        )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with _temporary_csv_file(out, policy.temp_name_style) as (handle, created_path):
            temp_path = created_path
            _write_projection(handle, projection)
            if policy.fsync_before_replace:
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(temp_path, out)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@contextmanager
def _temporary_csv_file(
    out: Path,
    style: TempNameStyle,
) -> Iterator[tuple[TextIO, Path]]:
    if style is TempNameStyle.NAMED_RANDOM:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=out.parent,
            prefix=f".{out.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            yield handle, Path(handle.name)
        return
    temp_path = out.with_name(f".{out.name}.{uuid.uuid4().hex}.tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        yield handle, temp_path


def validate_csv_output_path(
    out_path: str | Path,
    protected_paths: Iterable[str | Path],
) -> Path:
    """Resolve and reject an output path against an adapter-defined protected set."""
    out = Path(out_path).expanduser().resolve()
    protected = {Path(path).expanduser().resolve() for path in protected_paths}
    if out in protected:
        raise ValueError(f"Result CSV path would overwrite a protected path: {out}")
    return out


def validate_summary_output_path(
    out_path: str | Path,
    input_path: str | Path,
    case_rows: Iterable[Mapping[str, object]],
) -> Path:
    """Reject a summary path that could destroy any input or planned artifact."""
    protected: list[str | Path] = [input_path]
    for row in case_rows:
        for raw_stl in str(row.get("stl_path", "")).split(";"):
            if raw_stl.strip():
                protected.append(raw_stl.strip())
        out_dir = Path(str(row.get("out_dir", "outputs"))).expanduser().resolve()
        case_id = str(row.get("case_id", "")).strip()
        if case_id:
            protected.extend((out_dir / f"{case_id}.vtp", out_dir / f"{case_id}.npz"))
    return validate_csv_output_path(out_path, protected)


def _write_projection(handle: TextIO, projection: CsvProjection) -> None:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(projection.columns)
    writer.writerows(tuple(row[name] for name in projection.columns) for row in projection.rows)


__all__ = (
    "DURABLE_CSV_WRITE_POLICY",
    "AtomicCsvWritePolicy",
    "TempNameStyle",
    "validate_csv_output_path",
    "validate_summary_output_path",
    "write_csv_atomic",
)
