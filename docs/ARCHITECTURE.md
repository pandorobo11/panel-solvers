# Architecture

## Goal

One repository owns the shared application and numerical pipeline, while each
physical model owns only its model-specific inputs, equations, scalars, and
signature payload. The architecture must preserve current public behavior during
incremental migration.

## Layers

```text
fmfsolver/newtsolver compatibility frontends
                    |
              panelsolver.app
                /       \
   panelsolver.models   panelsolver.core
                |
          panelsolver.core
```

`panelsolver.core` will own geometry/mesh validation, attitude and frame
transforms, panel flow state, shielding, integration, component aggregation,
signatures, artifacts, caching, and execution/scheduling. It cannot know which
physical model is selected.

`panelsolver.models` will contain independent Sentman and hypersonic models. Each
model parses its own case fields, evaluates local panel loads, provides display
scalars/metadata, and provides a canonical signature payload.

`panelsolver.app` will own shared CLI/GUI orchestration through a solver
specification. `fmfsolver` and `newtsolver` will remain thin compatibility
frontends for existing entry points and imports.

## Central contracts

Phase 2 adopts the exact Python API in ADR 0002. Immutable, validated data and the
model protocol are exported from `panelsolver.core`; explicit model registration
and dispatch live in `panelsolver.models`. The semantic boundary is:

```text
PanelGeometry + PanelFlowState + model case
                         |
                  PanelLoadModel
                         |
LocalLoads(local traction coefficient vector, cell scalars, metadata)
                         |
        common force/moment integration and artifacts
```

The load vector is expressed per panel in an explicit frame and has shape
`(n_faces, 3)`. The shared integrator applies face area, reference area, reference
lengths, and moment reference point. It must not reconstruct tangential physics
from `Cp`.

Core owns `PanelGeometry`, `PanelFlowState`, `LocalLoads`, common/model case
payloads, and common result envelopes without importing a concrete model. The
models layer owns `ModelRegistry`, whose dispatch path validates the same
`PanelLoadModel` protocol for every registered model. Contract arrays are private,
read-only copies; metadata is deeply immutable. Physical equations, integration,
artifact projection, and legacy adapters are not part of Phase 2.

Phase 3 begins with pure frame primitives in `panelsolver.core`. They construct
`velocity_hat_stl` from already-resolved tangent angles, map STL-axis vectors to
body axes, and rotate body-axis vectors into stability axes. They preserve any
leading array dimensions and validate the trailing vector dimension explicitly.
Legacy attitude-mode parsing and public angle-domain policy remain adapter-owned,
so this extraction does not select either behavior recorded in D007.

The topology contract pairs immutable vertices and triangular face indices with
an already-validated `PanelGeometry` and ordered component/source metadata. It
checks indexing and one-to-one face alignment but does not load or repair a mesh,
derive geometric quantities, reject unresolved degeneracy, or select either
mesh-strictness behavior recorded in D011.

Common integration applies panel area/reference-area normalization to the local
traction vector, transforms total force into body and stability frames, and
computes body-axis moments about the configured STL-frame reference point. It
retains per-face force and moment contributions for later component aggregation
without importing or identifying a physical model.

## Ownership constraints

| Concern | Owner |
|---|---|
| STL loading, validation, components, fingerprint | core |
| attitude and coordinate transforms | core |
| shielding and ray backend selection | core |
| force/moment integration and aggregation | core |
| caches, scheduler, cancellation, progress | core |
| artifact envelope and common signature | core |
| Sentman equations and atmosphere inputs | Sentman model |
| Newtonian/wedge/cone/Prandtl–Meyer equations | hypersonic model |
| model case payload, scalars, algorithm version | each model |
| CLI/GUI flow and viewer | app |
| old names/options/import forwarding | compatibility frontend |

The common engine must not contain branches on a concrete model name. Models must
not write files, drive GUI state, or run the scheduler.

## GUI target

One shared GUI shell receives a solver specification containing identity, window
title, case schema, load model, and preferred display scalars. The viewer discovers
available VTP cell arrays dynamically. Existing `fmfsolver` and `newtsolver`
launchers select the appropriate specification.

## Signature target

The common signature envelope will include schema version, geometry fingerprint,
normalized common case, model ID, model algorithm version, and normalized model
case. Application/UI-only version changes must not invalidate numerical caches.
The exact schema is decided in Phase 5 under ADR 0005.
