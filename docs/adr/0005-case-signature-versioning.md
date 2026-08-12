# ADR 0005: Canonical numerical signatures separate schema and algorithms

- Status: Accepted (exact Phase 5 schema adopted)
- Date: 2026-08-12

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

## Consequences

UI and documentation changes need not invalidate calculations, while geometry,
physical-model, shielding-algorithm, and effective-backend changes do. Each model
owns and increments its algorithm version and signature payload. A field,
normalization, or serialization change requires a schema-version increment,
legacy-match migration tests, cache-isolation regression tests, and documented
artifact precedence; silent changes are prohibited.
