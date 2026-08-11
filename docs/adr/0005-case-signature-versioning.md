# ADR 0005: Separate signature schema and algorithm versions

- Status: Accepted (envelope decision; exact schema deferred to Phase 5)
- Date: 2026-08-12

## Context

Both legacy applications use case signatures for cached results and VTP matching,
but normalize inputs differently. Tying cache invalidation to the whole application
version would discard valid results after UI-only changes; omitting model/geometry
versions could reuse invalid results.

## Decision

Build a canonical signature envelope from a signature-schema version, content-
based geometry fingerprint, normalized common case, model ID, model algorithm
version, and normalized model-case payload. Keep the user-visible application
version in artifact metadata but outside numerical cache identity unless it changes
an explicitly versioned algorithm. Define canonical serialization and legacy
fallback/precedence in Phase 5 with Phase 1 fixtures.

## Consequences

UI and documentation changes need not invalidate calculations, while geometry and
physical changes do. Each model owns and increments its algorithm version and
signature payload. Schema migrations require explicit compatibility tests; silent
changes to signature inputs are prohibited.
