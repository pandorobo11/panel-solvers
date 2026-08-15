"""newtsolver parallel call shape over the shared scheduler."""

from panelsolver._compat.legacy_scheduler import (
    iter_legacy_case_results_parallel,
    resolve_legacy_parallel_chunk_cases,
)


def resolve_parallel_chunk_cases() -> int:
    return resolve_legacy_parallel_chunk_cases("NEWTSOLVER")


def iter_case_results_parallel(
    df,
    exec_order,
    workers,
    run_case_fn,
    *,
    chunk_cases=None,
    cancel_cb=None,
):
    yield from iter_legacy_case_results_parallel(
        df,
        exec_order,
        workers,
        run_case_fn,
        legacy_env_prefix="NEWTSOLVER",
        chunk_cases=chunk_cases,
        cancel_cb=cancel_cb,
    )


__all__ = ("iter_case_results_parallel", "resolve_parallel_chunk_cases")
