# Python API support policy

## Stable high-level API

The `panelsolver` package root exports only the first-release in-memory API:

```python
from panelsolver import (
    HypersonicCase,
    ResolvedAttitude,
    SentmanCase,
    SolveResult,
    resolve_attitude,
    solve_hypersonic,
    solve_sentman,
)
```

`SentmanCase` and `HypersonicCase` are separate types with separate required
physical inputs. Both state their ordered STL paths, STL scale, reference area,
moment reference in STL axes, three reference lengths, and a
`ResolvedAttitude`. `SentmanCase` uses resolved Mode A inputs (`speed_ratio`,
translational temperature, and wall temperature); atmosphere-based Mode B
resolution remains available through the lower-level model API.

`solve_sentman()` and `solve_hypersonic()` call the existing shared numerical
pipeline. They do not create Summary CSV, VTP, PNG, temporary output directories,
or any other filesystem artifact. `SolveResult.coefficients` exposes integrated
coefficients; components, geometry, shielding state, per-face traction and model
scalars remain available on the same in-memory result. Filesystem-producing
batch work is an explicit CLI operation, not a side effect of these functions.

## Lower-level architecture API

`panelsolver.core`, `panelsolver.models`, and `panelsolver.app` expose typed
contracts and composition functions used by the applications. They are useful
for development and advanced integrations, and the central load-vector contract
is recorded in [ADR 0002](../adr/0002-panel-load-vector-contract.md). They remain
lower-level architecture surfaces: callers must construct validated geometry,
flow, model, signature, and execution policy objects explicitly.

These modules are not re-exported wholesale from the package root.

## Best-effort compatibility API

Legacy paths under `fmfsolver` and `newtsolver`, including `run_case`,
`run_cases`, exporters, mesh/shielding helpers, and model-specific helpers, remain
importable on a best-effort basis. Exact keyword names, function/class identity,
defining module, qualname, pickle global, cache object, exception text or chain,
traceback, and validation timing are not compatibility contracts.

Their implementation is isolated under private `panelsolver._compat`. That
package is not a public API and may change without deprecation. The former
internal `panelsolver.app.legacy_*` module paths have been removed rather than
keeping app-to-compatibility reverse dependencies; use the product frontend
paths for best-effort direct calls.

Direct calls that bypass `read_cases()` must supply the fields their adapter
needs; file-reader defaults are not guaranteed to be inserted. Prefer the case
file plus CLI interface for durable automation. See
[Compatibility](compatibility.md) and [ADR 0008](../adr/0008-supported-domain-compatibility.md).

## Test-policy classification

- Release contracts are covered by command, normal GUI, case-table,
  Summary CSV/VTP, installed-wheel, and supported numerical regression tests.
- Direct-Python tests under the compatibility suite are best-effort smoke and
  diagnostic coverage; exact identity, qualname, traceback, and cache details
  asserted by historical tests do not promote those details to public contract.
- Phase 1 fixtures/goldens and Phase 3 adapter regressions are historical
  evidence and remain read-only inputs to compatibility decisions.
