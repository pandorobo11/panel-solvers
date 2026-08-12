"""newtsolver selection policy for the shared Phase 6 GUI."""

from __future__ import annotations

from collections.abc import Mapping

from panelsolver.app import ClosePolicy, SolverGuiAdapters, SolverSpec

from .csv_adapter import CSV_PROJECTION_POLICY

_PREFERRED_SCALARS = (
    "Cp_n",
    "shielded",
    "theta_deg",
    "area_m2",
    "center_x_stl_m",
    "center_y_stl_m",
    "center_z_stl_m",
    "stl_index",
)


def _present(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    return text


def _attitude_fields(row: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    attitude = (_present(row.get("attitude_input")) or "beta_tan").lower()
    alpha = row.get("alpha_deg")
    beta = row.get("beta_or_bank_deg")
    if attitude == "beta_sin":
        return (("alpha_t", alpha), ("beta_s", beta))
    if attitude == "bank":
        return (("alpha_i", alpha), ("phi", beta))
    return (("alpha_t", alpha), ("beta_t", beta))


def format_case(row: Mapping[str, object]) -> str:
    """Return the pinned hypersonic overlay fields without evaluating physics."""
    fields: list[tuple[str, object]] = [
        ("case_id", row.get("case_id")),
        ("Mach", row.get("Mach")),
        ("gamma", row.get("gamma")),
        ("w_eq", row.get("windward_eq")),
        ("l_eq", row.get("leeward_eq")),
    ]
    fields.extend(_attitude_fields(row))
    fields.extend(
        (
            ("shield", row.get("shielding_on")),
            ("ray", row.get("ray_backend")),
        )
    )
    return " | ".join(
        f"{name}={text}"
        for name, value in fields
        if (text := _present(value)) is not None
    )


def solver_spec(*, adapters: SolverGuiAdapters | None = None) -> SolverSpec:
    """Return the newtsolver identity and retained GUI policies."""
    return SolverSpec(
        product_id="newtsolver",
        model_id="hypersonic",
        window_title="newtsolver (GUI)",
        case_columns=CSV_PROJECTION_POLICY.input_columns,
        preferred_scalars=_PREFERRED_SCALARS,
        format_case=format_case,
        close_policy=ClosePolicy.IMMEDIATE,
        adapters=adapters,
    )


__all__ = ("format_case", "solver_spec")
