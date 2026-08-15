"""Legacy forwarding surface for the canonical FMF case-table policy."""

from panelsolver.domains.fmf import (
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
