"""Legacy forwarding surface for the canonical Hypersonic case-table policy."""

from panelsolver.domains.hypersonic import (
    CASE_READER_POLICY,
    DEFAULTS,
    INPUT_COLUMN_ORDER,
    InputValidationError,
    ValidationIssue,
    read_cases,
)

__all__ = (
    "CASE_READER_POLICY",
    "DEFAULTS",
    "INPUT_COLUMN_ORDER",
    "InputValidationError",
    "ValidationIssue",
    "read_cases",
)
