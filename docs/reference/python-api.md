# Python API support policy

The supported product compatibility surface is the CLI, normal GUI operation,
documented case files, and documented Summary CSV/VTP semantics. There is currently
no promised high-level `panelsolver` Python convenience API; the package root
intentionally exports no names.

## Neutral modules

`panelsolver.core`, `panelsolver.models`, and `panelsolver.app` expose typed
contracts and composition functions used by the applications. They are useful
for development and advanced integrations, and the central load-vector contract
is recorded in [ADR 0002](../adr/0002-panel-load-vector-contract.md). They remain
lower-level architecture surfaces: callers must construct validated geometry,
flow, model, signature, and execution policy objects explicitly.

## Compatibility modules

Legacy paths under `fmfsolver` and `newtsolver`, including `run_case`,
`run_cases`, exporters, mesh/shielding helpers, and model-specific helpers, remain
importable on a best-effort basis. Exact keyword names, function/class identity,
defining module, qualname, pickle global, cache object, exception text or chain,
traceback, and validation timing are not compatibility contracts.

Direct calls that bypass `read_cases()` must supply the fields their adapter
needs; file-reader defaults are not guaranteed to be inserted. Prefer the case
file plus CLI interface for durable automation. See
[Compatibility](compatibility.md) and [ADR 0008](../adr/0008-supported-domain-compatibility.md).
