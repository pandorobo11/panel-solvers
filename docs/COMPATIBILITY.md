# Compatibility contract

Compatibility is preserved per migrated surface, not asserted globally. During
Phase 0, the new distribution intentionally exposes only importable placeholder
packages; legacy repositories remain the supported calculators.

## Surfaces to preserve

| Surface | Required target | Freeze phase |
|---|---|---|
| Commands | `fmfsolver`, `fmfsolver-gui`, `fmfsolver-cli`, `newtsolver`, `newtsolver-gui`, `newtsolver-cli` | 1 and 7 |
| Python imports | public imports discovered from source/tests and real usage | 1 |
| Case input | CSV/Excel column names, defaults, validation, path resolution, row selection | 1 |
| Result CSV | column names, order, row scopes, blank/value semantics | 1 |
| VTP | cell arrays, field metadata, case-signature matching | 1 |
| NPZ | array names, shapes, values, metadata | 1 |
| GUI | case selection/run/cancel, viewer scalars, export, VTP matching | 1 and 6 |
| Environment | current backend/cache/worker variables and precedence | 1 and 5 |
| Numerical results | panel loads, masks, totals, components, force/moment transforms | 1 |

No legacy option, field, or behavior may be deleted because it appears unused.
Deprecation requires evidence, an announced transition, tests for the warning and
fallback, and a separately approved removal phase.

## Comparison rules

- CSV comparison is schema- and value-aware, including order when consumers may
  rely on it.
- VTP and NPZ comparison uses named arrays, shapes, values, and metadata rather
  than serialized bytes.
- Floating values use per-quantity tolerances with special treatment for values
  near zero.
- Paths, timestamps, backend identities, and nondeterministic metadata are
  normalized only when explicitly documented.
- A legacy discrepancy is recorded as two contracts until an ADR selects a
  unified behavior and defines compatibility handling.

The Phase 1 evidence is frozen in `phase1/BEHAVIORAL_INVENTORY.md`, the dual
contract ledger in `phase1/LEGACY_DIFFERENCES.md`, and semantic artifact captures
under `tests/fixtures/phase1`. Per-quantity limits and normalization are defined
in `phase1/TOLERANCES.md`; they are not a repository-wide license for numerical
drift.

## Compatibility frontends

`src/fmfsolver` and `src/newtsolver` may parse or translate legacy interfaces,
select a solver specification, and forward calls. They may not own physical
equations, geometry, integration, caching, scheduling, artifact generation, or
new application behavior.

## Current implementation status

- All six legacy console commands are registered; exact batch help and installed
  execution are checked on Ubuntu, Windows, and macOS.
- The complete frozen FMF and newtsolver module inventories and representative
  call shapes are forwarded. Product roots retain `__all__ = []`, compatibility
  versions remain distinct, and newtsolver's explicit D025 underscore exports
  are preserved without adding them to FMF.
- The Phase 6 shared GUI shell, cases panel, viewer, lifecycle, and image export
  now receive complete product adapters by default. Both compatibility GUI
  launchers read cases, execute, checkpoint, write results, and match primary or
  ordered legacy artifact signatures. An explicitly adapter-free `SolverSpec`
  remains a failing test/configuration path; it is not used by either launcher.
- Compatible CSV/Excel readers and runtime VTP/NPZ/summary-CSV serialization are
  implemented. Product policies retain worker logging, failure-partial behavior,
  output collision scope, CSV durability, compatibility versions, and model-only
  output fields independently.
- The shared Sentman and hypersonic models are forwarded through product-only
  compatibility modules; the frontends contain no copied physical equations.
- The Phase 3 CSV and semantic artifact projections are composed with the Phase
  5 engine and are also reachable through the frozen legacy Python call shapes.

Phase 7 is not complete until Issue #52 supplies final installed-sample/release
documentation and records both manual macOS GUI smokes. Until that acceptance is
merged, continue treating the pinned legacy products as the release baseline.
