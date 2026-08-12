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

## Current implementation non-compatibilities

- Legacy console commands are not registered.
- Legacy Python modules beyond the Phase 3 CSV/computed-data adapters do not exist.
- No CSV/Excel input reader, VTP/NPZ serializer, scheduler, CLI, or GUI is
  implemented. The shared STL loader and shielding engine are internal Phase 5
  migration surfaces, not legacy Python-import or command compatibility.
- The shared Sentman and hypersonic models are internal Phase 4 migration
  surfaces; legacy computational imports and commands are not forwarded yet.
- The Phase 3 CSV writer and semantic VTP/NPZ projections are internal migration
  surfaces, not a runnable solver pipeline.

These gaps are intentional and must not be mistaken for a usable preview release.
Continue using the pinned legacy products for calculations until their later
migration phases are accepted.
