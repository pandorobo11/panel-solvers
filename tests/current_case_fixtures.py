"""Build current case tables from read-only Phase 1 input evidence."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

import pandas as pd


def read_current_cases(
    reader: Callable[[str | Path], pd.DataFrame],
    historical_path: str | Path,
) -> pd.DataFrame:
    """Read a Phase 1 CSV after removing only the retired input field."""
    source = Path(historical_path)
    frame = pd.read_csv(source)
    frame = frame.drop(columns=["save_npz_on"])
    frame["stl_path"] = frame["stl_path"].map(
        lambda value: ";".join(
            str((source.parent / token.strip()).resolve())
            for token in str(value).split(";")
        )
    )
    frame["out_dir"] = frame["out_dir"].map(
        lambda value: str((source.parent / str(value)).resolve())
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        current_path = Path(temp_dir) / source.name
        frame.to_csv(current_path, index=False)
        return reader(current_path)
