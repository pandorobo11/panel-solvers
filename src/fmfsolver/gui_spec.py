"""FMF selection policy for the shared Phase 6 GUI."""

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
_DEFAULT_ADAPTERS = object()


def _present(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    return text


def format_case(row: Mapping[str, object]) -> str:
    """Return the pinned FMF overlay fields without evaluating physics."""
    fields: list[tuple[str, object]] = [("case_id", row.get("case_id"))]
    if _present(row.get("S")) and _present(row.get("Ti_K")):
        fields.extend(
            (("mode", "A"), ("S", row.get("S")), ("Ti", row.get("Ti_K")))
        )
    elif _present(row.get("Mach")) and _present(row.get("Altitude_km")):
        fields.extend(
            (
                ("mode", "B"),
                ("Mach", row.get("Mach")),
                ("Alt_km", row.get("Altitude_km")),
            )
        )
    fields.append(("Tw", row.get("Tw_K")))
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


def _attitude_fields(row: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    attitude = (_present(row.get("attitude_input")) or "beta_tan").lower()
    alpha = row.get("alpha_deg")
    beta = row.get("beta_or_bank_deg")
    if attitude == "beta_sin":
        return (("alpha_t", alpha), ("beta_s", beta))
    if attitude == "bank":
        return (("alpha_i", alpha), ("phi", beta))
    return (("alpha_t", alpha), ("beta_t", beta))


def solver_spec(
    *,
    adapters: SolverGuiAdapters | None | object = _DEFAULT_ADAPTERS,
) -> SolverSpec:
    """Return the FMF product identity with real adapters by default."""
    selected_adapters: SolverGuiAdapters | None
    if adapters is _DEFAULT_ADAPTERS:
        from .runtime import GUI_ADAPTERS

        selected_adapters = GUI_ADAPTERS
    else:
        selected_adapters = adapters  # type: ignore[assignment]
    return SolverSpec(
        product_id="fmfsolver",
        model_id="sentman",
        window_title="Sentman FMF Solver (GUI)",
        case_columns=CSV_PROJECTION_POLICY.input_columns,
        preferred_scalars=_PREFERRED_SCALARS,
        format_case=format_case,
        close_policy=ClosePolicy.DEFER_UNTIL_IDLE,
        adapters=selected_adapters,
    )


__all__ = ("format_case", "solver_spec")
