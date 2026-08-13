# Compatibility contract

ADR 0008 defines compatibility inside the supported domain. Phase 1 evidence
continues to record all pinned differences, but invalid-input quirks and Python
implementation details are not automatically permanent product contracts.

Compatibility is preserved per migrated surface, not asserted globally. During
Phase 0, the new distribution intentionally exposes only importable placeholder
packages; legacy repositories remain the supported calculators.

## Surfaces to preserve

| Surface | Required target | Freeze phase |
|---|---|---|
| Commands | `fmfsolver`, `fmfsolver-gui`, `fmfsolver-cli`, `newtsolver`, `newtsolver-gui`, `newtsolver-cli` | 1 and 7 |
| Python packages | `fmfsolver` and `newtsolver` package names; direct Python call shapes are best effort | 1 and 8 |
| Case input | CSV/Excel column names, defaults, validation, path resolution, row selection | 1 |
| Result CSV | column names, order, row scopes, blank/value semantics | 1 |
| VTP | cell arrays, field metadata, case-signature matching | 1 |
| NPZ | array names, shapes, values, metadata | 1 |
| GUI | case selection/run/cancel, viewer scalars, export, VTP matching | 1 and 6 |
| Environment | current backend/cache/worker variables and precedence | 1 and 5 |
| Numerical results | panel loads, masks, totals, components, force/moment transforms | 1 |

No documented command, normal GUI operation, model-specific input/output field,
or supported numerical behavior may be deleted because it appears unused.
Deprecation of those surfaces requires evidence, an announced transition, tests
for the warning and fallback, and a separately approved removal phase.

Exact direct-Python keyword names, direct GUI methods, function/class identity,
`__module__`, `__qualname__`, pickle globals, cache objects, `cache_info()`, exact
exception messages or chains, traceback structure, validation timing, logger
line ordering, and accidental invalid-input NaN/broadcast behavior are excluded
unless another ADR explicitly adopts a neutral public API.

## Comparison rules

- CSV comparison is schema- and value-aware, including order when consumers may
  rely on it.
- VTP and NPZ comparison uses named arrays, shapes, values, and metadata rather
  than serialized bytes.
- Floating values use per-quantity tolerances with special treatment for values
  near zero.
- Paths, timestamps, backend identities, and nondeterministic metadata are
  normalized only when explicitly documented.
- A supported-domain legacy discrepancy remains recorded until an ADR selects a
  unified behavior and defines compatibility handling. ADR 0008 already selects
  common safety/convergence for invalid inputs and excluded Python internals.

The Phase 1 evidence is frozen in `phase1/BEHAVIORAL_INVENTORY.md`, the dual
contract ledger in `phase1/LEGACY_DIFFERENCES.md`, and semantic artifact captures
under `tests/fixtures/phase1`. Per-quantity limits and normalization are defined
in `phase1/TOLERANCES.md`; they are not a repository-wide license for numerical
drift.

## Compatibility frontends

`src/fmfsolver` and `src/newtsolver` may parse or translate model-specific input
and output schemas, select a solver specification, retain migration names, and
forward calls. They may not own physical equations, common validation or
exceptions, geometry, integration, caching, scheduling, artifact generation,
GUI implementation, or new application behavior.

## Supported-domain safety

Shared boundaries reject NaN, infinity, numeric booleans, invalid/ragged shapes,
overflowed derived state, degenerate geometry, and zero or negative reference
quantities. Products do not preserve accidental propagation or an early return
that bypasses invalid normalization. Exception categories and field attribution
remain diagnostic; exact wording, cause/context, traceback, and timing do not.
Sentman Mode B therefore rejects a finite Mach value when the pinned computation
order overflows its derived speed ratio; finite positive derived values retain
the same formula and result.
Direct Sentman helpers validate reference area, physical scalars, unit vectors,
and shielding masks before computation. A valid shielded panel remains exact
zero, but shielding does not hide invalid normalization input.

Reader boundary coverage uses the following ADR 0008 matrix. Tests assert the
shared exception category, accept/reject decision, and diagnostic field, not
exact message text, issue order, cause/context, traceback, or timing.

| Field class | Zero | Negative finite | NaN | +Inf | -Inf |
|---|---:|---:|---:|---:|---:|
| Shared positive: STL scale, reference area, three reference lengths | reject | reject | reject | reject | reject |
| Shared signed: two attitude inputs, three reference coordinates | accept | accept | reject | reject | reject |
| FMF positive: `S`, `Ti_K`, `Mach`, `Tw_K` | reject | reject | reject | reject | reject |
| FMF altitude in the supported atmosphere table | accept | reject | reject | reject | reject |
| newtsolver model fields: `Mach`, `gamma` | reject | reject | reject | reject | reject |

FMF Mode A/Mode B pair diagnostics may attribute an absent NaN cell to its
mode-field pair as well as to the individual field. Fields that exist in only
one model remain model-specific.

D015 now uses common `FORWARD / YIELD_COMPLETED` behavior for both products.
Worker logs and warnings cross the process boundary, and successful earlier
cases from a later-failing chunk remain visible in input-ordered progress and
checkpoint snapshots while the remote failure is retained.

## Current implementation status

- All six legacy console commands are registered; batch help semantics and
  installed execution are checked on Ubuntu, Windows, and macOS.
- The complete frozen FMF and newtsolver module inventories and representative
  call shapes are forwarded. Product roots retain `__all__ = []`, compatibility
  versions remain distinct, and newtsolver's explicit D025 underscore exports
  are preserved without adding them to FMF.
- The Phase 6 shared GUI shell, cases panel, viewer, lifecycle, and image export
  now receive complete product adapters by default. Both compatibility GUI
  launchers read cases, execute, checkpoint, write results, and match primary or
  ordered legacy artifact signatures. An explicitly adapter-free `SolverSpec`
  remains a failing test/configuration path; it is not used by either launcher.
- Shared CSV/Excel format dispatch, portable Unicode case-ID validation,
  casefold collision detection, attitude domains, and CLI selection cardinality
  are implemented. Product readers retain only model schemas, defaults, physical
  fields, and their field validation. Both CLI and GUI reject summary collision
  with input/STL/planned VTP/NPZ paths regardless of save flags. Summary and
  checkpoint CSV use same-directory temporary files, flush, `fsync`, and atomic
  replace while retaining product schema/order/value semantics.
- The shared Sentman and hypersonic models are forwarded through product-only
  compatibility modules; the frontends contain no copied physical equations.
- Both frontends use strict shared mesh safety: non-finite or degenerate geometry,
  repair exceptions, and winding that remains inconsistent after repair are
  rejected. Valid face order, component IDs, fingerprints, and numerical results
  remain unchanged.
- The Phase 3 CSV and semantic artifact projections are composed with the Phase
  5 engine and are also reachable through the frozen legacy Python call shapes.

Phase 7 is complete. The clean installed wheel runs both unchanged Phase 1
sample sets and imports both frozen module inventories. Computer Use manually
confirmed both real macOS GUI launchers through input load, execution, progress,
matching VTP display, scalar/camera controls, PNG export, and close. The exact
evidence is in `PHASE7_EXECUTION_RECORD.md`; installation and rollback are in
`PHASE7_USER_GUIDE.md`.

This is migration compatibility acceptance, not final Phase 8 acceptance. ADR
0008 now governs the remaining audit and remediation. No migration package or
command name is deprecated and the pinned legacy repositories remain unarchived
references.
