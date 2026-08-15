# Architecture

The completed software ships one distribution with a shared model-neutral engine
and application layer, two independent physical models, and thin compatibility
frontends.

```text
fmfsolver / newtsolver compatibility frontends
                         |
                   panelsolver.app
                    /          \
        panelsolver.models   panelsolver.core
                    |
              panelsolver.core
```

## Layer ownership

| Layer | Owns |
|---|---|
| `panelsolver.core` | immutable contracts, geometry, frames, shielding, integration, aggregation, signatures, mesh/shielding caches, scheduler |
| `panelsolver.models` | Sentman and hypersonic case validation, equations, model scalars, model signature payloads |
| `panelsolver.app` | case-table mechanics, product assembly, CLI/GUI orchestration, artifact and CSV serialization |
| `fmfsolver`, `newtsolver` | legacy names, model schemas/defaults, compatibility versions, product projection policy |

Allowed dependency directions are `app -> models -> core`, `app -> core`, and
compatibility frontends inward to those layers. Core cannot import models, app,
GUI, or a compatibility frontend; models cannot import app, GUI, or a frontend.
Physical equations do not belong in GUI or compatibility code.

## Numerical boundary

Every model receives validated `PanelGeometry` and `PanelFlowState` and returns a
`LocalLoads` vector of shape `(n_faces, 3)`. This is deliberately not a universal
pressure coefficient: Sentman has a tangential contribution, while the
hypersonic model returns pressure-only normal traction. Core applies panel area
and reference normalization and integrates forces and moments.

The exact contract and immutability rules are in
[ADR 0002](../adr/0002-panel-load-vector-contract.md). Units, frames, and signs
are in [Numerical conventions](../reference/numerical-conventions.md).

## Execution and artifacts

The one-case engine loads ordered STL components, validates geometry, resolves
shielding, evaluates a registered model, integrates totals/components, and
returns a canonical signature with immutable results. The spawn scheduler wraps
that engine and rebuilds snapshots in input order.

CSV and VTP projections receive explicit product policy. Shared code does
not branch on a concrete model name to invent a universal schema. Compatibility
frontends supply only model-specific input/output additions and version policy.

## Stable decisions

Architecture changes must respect the accepted [ADRs](../adr/README.md),
especially dependency direction, the load-vector boundary, signatures, mesh
identity, distribution versioning, and supported-domain compatibility.
Historical Phase 1–8 design/evidence is retained under
[History](../history/README.md), but its migration sequencing is no longer the
current development model.
