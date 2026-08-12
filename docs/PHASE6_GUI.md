# Phase 6 shared GUI and viewer

Phase 6 migrates the duplicated Qt/PyVista shell behind one model-neutral
`SolverSpec`. It does not complete case-file compatibility, artifact
serialization, command registration, packaging, or public import forwarding;
those remain Phase 7 work.

## Dependency sequence

The implementation is serialized as follows:

1. `SolverSpec` and product-selected presentation/lifecycle policies;
2. headless artifact matching and dynamic scalar discovery;
3. the shared VTP viewer and camera controls;
4. case loading, table selection, and automatic viewer matching;
5. progress, cooperative cancellation, and close lifecycle;
6. single and selected-case image export;
7. shared bootstrap, thin compatibility launchers, and final acceptance.

Each slice starts from the latest accepted `main`, uses one issue and one
worktree, and is merged only after the complete local and cross-platform gates
pass.

## Solver specification boundary

`panelsolver.app.SolverSpec` carries product identity, model identity, exact
window title, ordered case-table columns, preferred display scalars, overlay
formatting, close policy, and an optional complete adapter bundle. Shared widgets
receive this object and never import a compatibility frontend or branch on a
model name.

The adapter bundle is deliberately optional in this phase. It defines the one
injection point for case reading, signature candidates, scheduled execution,
result-path validation, and resolved wind direction. The product-compatible
implementations remain Phase 7 work; Phase 6 widgets are tested with injected
adapters and headless fixtures.

## Retained product differences

- D022 remains exact: FMF uses `Sentman FMF Solver (GUI)` and newtsolver uses
  `newtsolver (GUI)`.
- D023/D027 are not normalized. FMF selects `defer_until_idle`; newtsolver
  selects `immediate`, retaining the absence of an equivalent close deferral in
  the pinned implementation.
- Product case schemas and overlay fields remain separate. FMF Mode A/B and
  thermal fields are not added to the hypersonic schema; hypersonic equation
  selectors are not added to FMF.
- Preferred scalar order is independently selected even where the current
  pinned lists are equal. Later viewer discovery must accept additional
  model-specific cell arrays dynamically (D019).

The close-policy choice records both observable contracts; it does not declare
either one a universal behavior.
