# Phase 4 physical-model adapters

Phase 4 moves only physical-model behavior behind the Phase 2
`PanelLoadModel` protocol. Geometry loading, shielding calculation, common
integration, artifact projection, execution, signatures, compatibility
frontends, and GUI behavior remain in their owning phases.

## Phase 4a: Sentman

`panelsolver.models.SentmanModel` uses the stable model ID `sentman` and
algorithm version `sentman-b62bc844`. Its numerical oracle is pinned
`fmfsolver` commit `b62bc844d02a8f5212e62a53dea3238a1414317d`.

The model payload keeps the two legacy flow modes separate:

- Mode A requires `S`, `Ti_K`, and `Tw_K`;
- Mode B requires `Mach`, `Altitude_km`, and `Tw_K`, then uses the pinned
  US1976 linear interpolation and mean-to-most-probable speed conversion.

The returned traction is the legacy Sentman vector numerator. This is a thin
normalization adapter, not a formula change: the old routine applied `/Aref`
inside the equation, while the adopted contract requires the common integrator
to apply `area_m2 / Aref_m2`. Both incident tangential/freestream and normal
reflected terms are retained. Shielded faces are exact-zero vectors.

`LocalLoads.cell_scalars` contains `Cp_n` and `theta_deg`. Model metadata contains
resolved `mode`, `S`, `Ti_K`, and `Tw_K`. `signature_payload()` returns only the
normalized raw model inputs and deliberately does not construct, serialize, or
hash the Phase 5 common signature envelope.

The required US1976 columns are transcribed from both pinned CSV files into
private numeric constants with source hashes. Model code imports no filesystem,
artifact, GUI, scheduler, application, or compatibility module.

Verification recomputes all six FMF Phase 1 cases, including Mode B, bank,
multi-component, and both shielding backends, then passes the model loads through
the Phase 3 integration and aggregation functions. Existing golden files and
tolerances are unchanged.

## Phase 4b: hypersonic

Pending. It remains a separate Issue/PR and must not reuse a Sentman case,
scalar, metadata, or equation superset.
