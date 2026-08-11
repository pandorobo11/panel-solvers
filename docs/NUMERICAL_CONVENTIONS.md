# Numerical conventions

This document records conventions already common to the two legacy interfaces.
Phase 1 verifies them against executable semantic goldens. The captured arrays,
relations, and evidence-based limits are documented in
`phase1/GOLDEN_BASELINES.md` and `phase1/TOLERANCES.md`. An unverified item is not
permission to normalize differing legacy behavior.

## Units and naming

- Internal physical quantities use SI units.
- Public case angles are in degrees; internal trigonometry uses radians.
- Names must identify units where ambiguity is likely (`Aref_m2`, `Lref_Cm_m`,
  `alpha_deg`) and identify frames (`_stl`, `_body`, `_wind`).
- Per-face scalar arrays have shape `(n_faces,)`; per-face vectors normally have
  shape `(n_faces, 3)`.
- Reference areas and reference lengths used as divisors must be finite and
  strictly nonzero. Geometry areas must be finite and nondegenerate.

## Attitude input

For the current tangent-angle convention:

```text
Vhat_stl = normalize([
    cos(alpha_t) cos(beta_t),
   -sin(beta_t) cos(alpha_t),
    sin(alpha_t) cos(beta_t),
])
```

Thus positive `alpha_t` points freestream toward `+Z_stl`, and positive `beta_t`
points it toward `-Y_stl`. The `beta_sin` and included-angle/bank inputs remain
public legacy alternatives and must resolve to the same explicit vector before
panel calculations. Their legacy domains and edge behavior are frozen in the
Phase 1 valid/invalid fixtures; differing product behavior remains separate.

## Local loads and integration

A model returns a nondimensional local traction-coefficient vector for every
panel. The semantic integration contract is:

```text
C_face_stl = traction_coeff_stl * (area_m2 / Aref_m2)
C_total_stl = sum(C_face_stl)
```

Moment coefficients use the cross product of the reference-point displacement
and face load, normalized by the corresponding roll, pitch, or yaw reference
length. Precise axes/signs and frame transforms must be copied from verified
legacy behavior, not reconstructed from convention alone.

The hypersonic pressure-only model can express local traction as
`-Cp * normal_out_stl`. The Sentman model can contain a freestream/tangential
component, so no common contract may replace the vector with a scalar `Cp`.

## Floating-point and exceptional values

- Use NumPy arrays of floating type appropriate to the verified legacy behavior;
  do not change precision as incidental cleanup.
- Validate shapes before relying on broadcasting.
- Reject or explicitly handle NaN, infinity, zero reference normalization, and
  degenerate faces.
- Do not hide domain errors by clipping unless the legacy contract and tests
  justify the exact clipping behavior.
- Regression comparisons use the Phase 1 case profile and quantity-specific
  absolute/relative tolerance. There is intentionally no repository-wide default
  tolerance.

## Frozen frame and sign evidence

Phase 1 fixtures now cover STL/body/stability transforms, force and moment signs,
reference offsets, windward/leeward classification, panel normal orientation,
and edge-angle cases. The pinned case JSON remains the executable authority; this
does not select one behavior where the legacy products differ.
