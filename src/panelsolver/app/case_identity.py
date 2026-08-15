"""Portable case-identity validation shared by application entry points."""

from __future__ import annotations

import unicodedata

_INVALID_CASE_ID_CHARS = frozenset('/\\<>:"|?*')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_case_id(value: object) -> str:
    """Return one portable NFC Unicode case identifier or raise ``ValueError``."""
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


__all__ = ("validate_case_id",)
