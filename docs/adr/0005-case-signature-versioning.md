# ADR 0005: Canonical numerical signatures separate schema and algorithms

- Status: Accepted (exact Phase 5 schema adopted)
- Date: 2026-08-12

The NPZ serialization portion of this decision is superseded by
[ADR 0009](0009-remove-npz-output.md). Its CSV, VTP, numerical-signature, and
cache-identity decisions remain in force.

## Context

Both legacy applications use case signatures for cached results and VTP matching,
but normalize inputs differently. Tying cache invalidation to the whole application
version would discard valid results after UI-only changes; omitting model/geometry
versions could reuse invalid results.

## Decision

Build the following exact schema, serialized as UTF-8 JSON with sorted keys,
compact separators, ASCII escaping, and non-finite values rejected. The case
signature is the lowercase SHA-256 digest of those bytes.

```text
schema: {name: "panelsolver.case", version: 1}
geometry: {fingerprint_sha256}
common_case: {
  case_id, Aref_m2, moment_reference_stl_m,
  Lref_Cl_m, Lref_Cm_m, Lref_Cn_m,
  alpha_t_deg, beta_t_deg
}
model: {id, algorithm_version, case}
shielding: {
  algorithm_version, enabled, requested_backend,
  effective_backend, batch_size
}
```

`model.case` is the model-owned normalized signature payload. The shielding
section includes the effective backend so `auto` results produced by rtree and
Embree cannot share a numerical result-cache entry. Cache capacity is excluded
because it cannot change numerical output. The user-visible application version
remains artifact metadata outside this identity.

The Phase 5 signature is always the primary match. Product adapters may supply
an ordered collection of opaque legacy hashes for fallback. Core tests the
primary first and never reconstructs, normalizes, or equates the path/version-
dependent D017 envelopes or the direct/file D018 default variants.

### Phase 8 result-cache clarification

The schema above remains the exact public and artifact signature. The common
execution API also accepts a supplied float64 flow-direction vector within its
documented angle-consistency tolerance and evaluates that accepted vector
without rounding. Because the exact vector is not a field in the frozen schema,
the execution engine derives a private, domain-separated result-cache signature
from the public digest plus the exact three float64 values used by the model.

That private identity is process-local cache state. It is not returned from
`execute_case`, serialized into CSV/VTP/NPZ, or considered during artifact
matching. This prevents a tolerance-distinct direct request from reusing another
request's numerical result while preserving every existing public digest and
fallback rule.

## Consequences

UI and documentation changes need not invalidate calculations, while geometry,
physical-model, shielding-algorithm, and effective-backend changes do. Each model
owns and increments its algorithm version and signature payload. A field,
normalization, or serialization change requires a schema-version increment,
legacy-match migration tests, cache-isolation regression tests, and documented
artifact precedence; silent changes are prohibited.
