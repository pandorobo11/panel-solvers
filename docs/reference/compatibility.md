# Compatibility policy

[ADR 0008](../adr/0008-supported-domain-compatibility.md) defines compatibility
inside the supported domain. The current supported surfaces are:

- canonical batch commands `panelsolver fmf` and
  `panelsolver hypersonic`;
- canonical GUI commands `panelsolver-gui fmf` and
  `panelsolver-gui hypersonic`;
- the stable package-root Python API listed in [Python API support](python-api.md);
- all six legacy compatibility commands: `fmfsolver`, `fmfsolver-gui`,
  `fmfsolver-cli`,
  `newtsolver`, `newtsolver-gui`, and `newtsolver-cli`;
- normal launcher-driven GUI operation;
- documented CSV/XLSX/XLSM case files and product schemas/defaults;
- documented Summary CSV and VTP semantics;
- supported numerical values, signs, frames, normalizations, and model-specific
  behavior.

Legacy direct-Python implementation details are best effort as described in
[Python API support](python-api.md). Invalid-input quirks, exact exceptions and
tracebacks, object identity, pickle globals, and cache internals are not frozen
product differences.

The canonical `fmf` token selects the free-molecular-flow domain and its current
Sentman model. `hypersonic` selects the hypersonic panel-method domain and its
Newtonian-family methods. Neither token identifies a legacy product. The naming
contract is recorded in [ADR 0011](../adr/0011-canonical-domain-naming.md).

Best-effort implementation lives in private `panelsolver._compat`, which points
only inward to the shared layers. Supported CLI/GUI runtime does not import that
package directly; the `fmfsolver` and `newtsolver` frontends select it only for
legacy direct-Python translation.

## Distribution and product versions

The single distribution is `panel-solvers`, currently version `0.1.0`. It owns
all three top-level packages. Product-facing compatibility versions remain:

| Frontend | Compatibility version |
|---|---:|
| fmfsolver | `1.3.8` |
| newtsolver | `1.0.3` |

Use `importlib.metadata.version("panel-solvers")` for the installed distribution
version. Compatibility versions appear only where the accepted product format
already exposed them. The shared and legacy distributions cannot safely coexist.

## Shared convergence

Both frontends use common strict mesh and numeric validation, portable case IDs,
case-table dispatch, output collision/durable CSV behavior, and scheduler
`FORWARD / YIELD_COMPLETED` policy. Model inputs/equations, product-only output
fields, legacy signatures, GUI identities, and migration command/package names
remain distinct where required.

The complete historical observations, including superseded differences, remain
under [Migration history](../history/migration/phase1/LEGACY_DIFFERENCES.md).
They are evidence, not an instruction to reintroduce unsafe behavior.
