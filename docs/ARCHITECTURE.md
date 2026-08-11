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

## Planned central contracts

The exact Python API is deliberately deferred to Phase 2, after Phase 1 regression
capture. The approved semantic boundary is:

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
