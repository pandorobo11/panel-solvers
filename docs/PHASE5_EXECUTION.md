# Phase 5 shared execution infrastructure

Phase 5 composes the already-accepted contracts and physical models into a
single model-neutral execution path. It does not add a CLI, GUI, artifact
serializer, or compatibility import surface.

## Geometry and shielding

The Phase 5a loader snapshots source STL bytes, applies SI scale and an explicit
normal-repair policy, then constructs immutable `PanelMesh` and `PanelGeometry`
contracts. ADR 0006 records retained D011 behavior and the content-safe D012
cache identity. The versioned numerical geometry fingerprint excludes paths and
timestamps but includes ordered topology, derived geometry, and component IDs.

Phase 5b casts one upstream ray from each face center with the pinned epsilon and
first-hit rule. Forced rtree and Embree never silently fall back. Cache identity
includes geometry, direction, effective backend, batch size, and shielding
algorithm version. `PANELSOLVER_SHIELD_*` takes precedence over one adapter-
selected legacy prefix; core never chooses between both legacy prefixes.

## Signature and result cache

ADR 0005 defines the exact schema. The signature binds common resolved inputs,
geometry, model identity/algorithm/payload, and requested/effective shielding
configuration. Application version and cache capacity are excluded. The result
cache stores only immutable `CommonResults`, so equivalent numerical geometry at
a different source path cannot reuse stale component-source metadata.

Phase 5 signatures match first. Product adapters may supply opaque ordered
legacy fallbacks; core does not normalize D017/D018 differences.

## One-case engine

`execute_case` accepts `CaseExecutionRequest`, whose model must implement the
Phase 2 `PanelLoadModel` and provide its normalized signature payload. The engine
validates model identity, loads geometry, computes shielding, constructs
`PanelFlowState`, builds the signature, checks the result cache, evaluates the
model, and routes the local vector through common integration and component
aggregation.

The engine has no concrete-model branch. `panelsolver.app` assembles the registry
containing `SentmanModel` and `HypersonicModel` and selects by stable model ID.
Models receive immutable geometry/flow contracts and never access files,
artifacts, GUI state, or scheduling.

The returned `CaseExecutionResult` contains the current mesh/source metadata,
exact shielding result, immutable `CommonResults`, canonical signature, warnings,
and cache-hit state. Artifact projection remains a separate Phase 3 operation;
serialization remains outside this engine.

## Deferred to Phase 5e

Worker processes, grouping, logging policy, cancellation, progress, partial
results, failure propagation, and checkpoint-ready snapshots remain scheduler
work. One-case execution raises the original model/geometry/shielding error and
does not catch it as a worker failure.
