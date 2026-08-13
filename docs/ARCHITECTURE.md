# Architecture

## Goal

One repository owns the shared application and numerical pipeline, while each
physical model owns only its model-specific inputs, equations, scalars, and
signature payload. ADR 0008 limits preserved product differences to those model
surfaces and migration names; common infrastructure and invalid-input safety
converge.

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

`panelsolver.models` contains independent Sentman and hypersonic models. Each
model parses its own case fields, evaluates local panel loads, provides display
scalars/metadata, and provides a canonical signature payload.

`panelsolver.app` owns shared GUI and CLI orchestration through product-selected
specifications and policies. `fmfsolver` and `newtsolver` remain thin
compatibility frontends for existing entry points and imports.

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
Legacy attitude-mode parsing remains application-owned. The shared case-reader
boundary applies the ADR 0008 public angle-domain policy before model adaptation;
the frame primitive only receives resolved angles.

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

Component aggregation groups those face contributions by the existing geometry
IDs in ascending order, applies the same global reference quantities, and builds
the already-adopted `ComponentResult` and `CommonResults` contracts. Component
metadata remains caller-supplied and model-neutral.

Artifact projection builds immutable semantic VTP/NPZ arrays from the mesh and
common results. Adapter-supplied policy data carries run metadata and explicit
product additions, so model-specific fields are preserved without a model-name
branch or a universal superset schema in core. Serialization and CSV writing are
separate concerns.

The Phase 7 application runtime composes adapted case requests, the shared
spawn scheduler, semantic projections, and filesystem serializers. Its runtime
policy requires each compatibility frontend to select worker-log and
failure-partial behavior, CSV schema/durability, compatibility version, and
model-specific projection additions explicitly. Successful checkpoint and final
snapshots are assembled in input order even when shielding reuse changes
execution order or workers complete out of order.

Phase 7 Python-import adapters restore the two frozen module inventories without
moving implementation back into the compatibility frontends. Shared application
adapters translate legacy DataFrames, result dictionaries, mutable mesh views,
direct serializers, and scheduler signatures. Model-specific public helpers
delegate to the same Sentman or hypersonic equations used by `PanelLoadModel`;
newtsolver's explicit D025 exports remain a product contract rather than a
common-model union. Product modules select strictness and worker policies and
perform only call-shape translation.

Summary CSV projection likewise receives an ordered schema from a product
adapter. Core calculates shared total/component cells while adapter-supplied run
values fill product fields. The FMF and newtsolver adapters retain separate
input/result column lists, collision sets, and atomic-write policies: FMF uses a
same-directory named temporary file plus flush/`fsync`, while newtsolver uses a
same-directory UUID name without explicit `fsync`. These policies preserve D009,
D010, and D029 without choosing a universal behavior.

The final Phase 3 adapter boundary accepts topology, geometry, shielding state,
and local traction that a legacy model has already computed. It derives the
resolved flow direction with the shared frame primitive, constructs the Phase 2
contracts, and routes one case through shared integration, aggregation, and all
three semantic projections. Product wrappers add only the explicit CSV/artifact
policy fields documented in `PHASE3_ADAPTERS.md`; they do not call or contain a
physical equation.

Phase 4a places the pinned Sentman vector equation and Mode A/B atmosphere
resolution behind `PanelLoadModel`. The model returns the legacy equation's
local numerator before reference-area normalization; the Phase 3 integrator
continues to own `area_m2 / Aref_m2`. `Cp_n` and `theta_deg` remain Sentman
visualization scalars, while resolved `mode`, `S`, `Ti_K`, and `Tw_K` remain
model metadata. Pinned US1976 interpolation columns are in-package numeric
constants, so model evaluation performs no filesystem access. The concrete
model exposes only its normalized model-case signature payload; signature
envelope construction remains Phase 5 work.

Phase 4b independently places Newtonian, modified-Newtonian, tangent-wedge,
tangent-cone, and Prandtl–Meyer behavior behind the same protocol. Its local
traction is pressure-only `-Cp * normal_out_stl`; core does not reconstruct it
from a shared scalar. Windward and leeward selector sets, one-or-per-component
expansion, Mach/gamma validation, detached branches, Taylor–Maccoll integration,
and inverse Prandtl–Meyer iteration remain owned by the hypersonic model. No
Sentman case field, scalar, or metadata superset is introduced.

Phase 5a adds model-neutral STL loading in core. It preserves the two recorded
normal-repair failure policies through an explicit loader option while always
enforcing the Phase 2 finite, positive-area geometry contract. Mesh-cache
identity uses source content, scale, policy, and loader version; a separate
versioned geometry fingerprint covers the ordered numerical mesh contract for
shielding, signatures, and later execution caches. Paths and file timestamps do
not define numerical geometry identity.

Phase 5b applies the pinned face-center, upstream, first-hit ray algorithm to a
`PanelMesh`. Explicit rtree and Embree adapters and `auto` selection stay in
core; requesting unavailable Embree is still an error. Shield-mask and
intersector identities include the Phase 5a geometry fingerprint, effective
backend, flow direction, batch size, and shielding algorithm version. Neutral
`PANELSOLVER_*` settings take precedence over one explicitly selected legacy
prefix, so core never guesses between FMF and newtsolver environment state.

Phase 5c adopts the exact ADR 0005 canonical signature. It binds normalized
common inputs, model-owned payload and algorithm version, numerical geometry,
and resolved shielding/backend identity without using the application version.
Primary Phase 5 matching precedes ordered, opaque legacy fallbacks supplied by
product adapters; core does not contain either legacy signature schema. The
shared result cache still accepts `CaseSignature` keys, but execution uses a
private, domain-separated signature that combines the public digest with the
exact accepted float64 flow direction. The private cache identity is never an
artifact or matching identity.

Phase 5d composes mesh loading, shielding, model evaluation, integration,
aggregation, signatures, and numerical-result caching into one one-case core
engine. The model supplies its normalized signature payload and local load
vector through protocols; core contains no Sentman/hypersonic branch. Application
assembly selects the registered model. Artifact writing, worker scheduling, and
GUI lifecycle remain outside the one-case engine.

Phase 5e adds a model-neutral spawn scheduler around that one-case engine.
Scheduling bucket keys are reuse hints only and never replace geometry,
shielding, or result-cache identities. Completion-order delivery carries stable
input indices; progress and checkpoint snapshots are rebuilt deterministically
in caller-defined input order. Cancellation is cooperative between cases and
does not interrupt an active ray query or model solve. D015 now uses common
`FORWARD / YIELD_COMPLETED` behavior for worker logs and failed-chunk completed
results. Worker startup failures, remote
tracebacks, and unexpected exits cross the process boundary as distinct errors.

Phase 6 adds one `SolverSpec`-driven Qt shell, cases panel, and PyVista viewer.
The spec carries product identity, exact title, ordered case columns, preferred
model scalars, overlay formatting, and adapter callbacks. Product-selected
legacy lifecycle policy is transitional rather than a permanent compatibility
requirement under ADR 0008. Widgets import neither compatibility frontend nor
concrete model. VTP
scalar discovery and exact case/signature matching are shared services; product
case schemas and overlays remain independent. QThread execution delegates case
I/O, scheduling policy, checkpoint/final serialization, and wind resolution to
adapters. The shared bootstrap supplies an explicitly non-calculating placeholder
when Phase 7 adapters are absent, allowing the shell to open without presenting
it as a migrated solver.

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
title, case schema, adapter callbacks, close behavior, overlay formatting, and
preferred display scalars. The viewer discovers available VTP cell arrays
dynamically. The thin `fmfsolver.app.gui_app` and `newtsolver.app.gui_app`
modules select the appropriate specification. The corresponding CLI selector
modules use the same real readers, runtime, and serializers, and all six legacy
console names are registered by the single distribution.

## Signature target

The common signature envelope will include schema version, geometry fingerprint,
normalized common case, model ID, model algorithm version, and normalized model
case. Application/UI-only version changes must not invalidate numerical caches.
The exact schema is decided in Phase 5 under ADR 0005.
