from __future__ import annotations

import os
import unittest
from pathlib import Path


def assert_paths_equivalent(
    test_case: unittest.TestCase,
    expected: str | os.PathLike[str],
    actual: str | os.PathLike[str],
) -> None:
    expected_path = Path(expected)
    actual_path = Path(actual)
    try:
        equivalent = os.path.samefile(expected_path, actual_path)
    except OSError:
        equivalent = expected_path.resolve(strict=False) == actual_path.resolve(
            strict=False
        )
    test_case.assertTrue(
        equivalent,
        f"Paths are not filesystem-equivalent: {expected_path!r} != {actual_path!r}",
    )
