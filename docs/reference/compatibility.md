# Compatibility policy

[ADR 0008](../adr/0008-supported-domain-compatibility.md) defines compatibility
inside the supported domain. The current supported surfaces are:

- all six commands: `fmfsolver`, `fmfsolver-gui`, `fmfsolver-cli`,
  `newtsolver`, `newtsolver-gui`, and `newtsolver-cli`;
- normal launcher-driven GUI operation;
- documented CSV/XLSX/XLSM/XLS case files and product schemas/defaults;
- documented Summary CSV and VTP semantics;
- supported numerical values, signs, frames, normalizations, and model-specific
  behavior.

Direct Python implementation details are best effort as described in
[Python API support](python-api.md). Invalid-input quirks, exact exceptions and
tracebacks, object identity, pickle globals, and cache internals are not frozen
product differences.

## Distribution and product versions

The single distribution is `panel-solvers`, currently version `0.1.0`. It owns
all three top-level packages. Product-facing compatibility versions remain:

| Frontend | Compatibility version |
|---|---:|
| FMF | `1.3.8` |
| newtsolver | `1.0.3` |

Use `importlib.metadata.version("panel-solvers")` for the installed distribution
version. Compatibility versions appear only where the accepted product format
already exposed them. The shared and legacy distributions cannot safely coexist.

## Shared convergence

Both frontends use common strict mesh and numeric validation, portable case IDs,
Excel dispatch, output collision/durable CSV behavior, and scheduler
`FORWARD / YIELD_COMPLETED` policy. Model inputs/equations, product-only output
fields, legacy signatures, GUI identities, and migration command/package names
remain distinct where required.

The complete historical observations, including superseded differences, remain
under [Migration history](../history/migration/phase1/LEGACY_DIFFERENCES.md).
They are evidence, not an instruction to reintroduce unsafe behavior.
