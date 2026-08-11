# ADR 0002: Put a local load vector at the model boundary

- Status: Accepted (semantic decision; exact API deferred to Phase 2)
- Date: 2026-08-12

## Context

Hypersonic models can often express panel traction as pressure coefficient times
the outward normal. The Sentman model also contains a freestream/tangential load
component. A common interface returning only `Cp` cannot represent both without
discarding physics or smuggling model-specific reconstruction into core.

## Decision

Each physical model returns a local nondimensional load vector for every panel,
plus named visualization scalars and model metadata. The shared engine applies
areas/reference quantities and integrates force and moment. Frames, shapes,
validation, ownership, and exact Python names will be fixed in Phase 2 after
Phase 1 numerical baselines exist.

## Consequences

The core can integrate all models uniformly and preserves Sentman tangential
loads. Model adapters must explicitly produce `(n_faces, 3)` vector data. Scalar
`Cp` remains available as model output for visualization/compatibility where
applicable, but is not the universal computational contract.
