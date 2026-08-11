# Numerical conventions

This document records conventions already common to the two legacy interfaces.
Phase 1 must verify them against executable golden cases. An unverified item is
not permission to normalize differing legacy behavior.

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
panel calculations. Their domains and edge behavior will be frozen in Phase 1.

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
- Regression comparisons use quantity-specific absolute/relative tolerances
  established in Phase 1; there is no repository-wide default tolerance yet.

## Frames and signs still to freeze

Phase 1 must explicitly fixture STL/body/stability transformations, force and
moment coefficient signs, center-of-moment handling, windward classification,
panel normal orientation, and edge angles. Until then, the pinned legacy outputs
are authoritative.
