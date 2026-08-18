# CLI guide

The canonical batch entry point selects a physical flow domain:

```text
panelsolver fmf --input PATH [--output PATH] [--workers N]
                [--cases ID [ID ...]] [--checkpoint-every-cases N]
panelsolver hypersonic --input PATH [--output PATH] [--workers N]
                       [--cases ID [ID ...]] [--checkpoint-every-cases N]
```

Here `fmf` means the free-molecular-flow domain selector. It is not the legacy
`fmfsolver` distribution or product identity. The selected physical model is
Sentman; the stable Python API names the domain as `FMFCase` and `solve_fmf()`.

| Selector | Flow-domain identity | Physical model identity | Reused case schema |
|---|---|---|---|
| `fmf` | free molecular flow | Sentman | FMF case table |
| `hypersonic` | hypersonic pressure approximation | Newtonian-family methods | Hypersonic case table |

The final column is a schema/application-service reuse choice, not the identity
of the canonical command.

The existing legacy compatibility batch commands remain and share the same
options:

```text
fmfsolver-cli --input PATH [--output PATH] [--workers N]
              [--cases ID [ID ...]] [--checkpoint-every-cases N]
newtsolver-cli --input PATH [--output PATH] [--workers N]
               [--cases ID [ID ...]] [--checkpoint-every-cases N]
```

All four batch forms use the same case-table reader and application service.
They accept CSV, XLSX, and XLSM. Summary CSV and optional per-case VTP are the
only formal outputs; legacy BIFF `.xls` and NPZ are not supported.

| Option | Meaning | Default |
|---|---|---|
| `-i`, `--input` | CSV/XLSX/XLSM case table | required |
| `-o`, `--output` | Summary CSV | `<input_dir>/outputs/<input_stem>_result.csv` |
| `-j`, `--workers` | Spawn workers; must be at least 1 | `1` |
| `--cases` | Space- or comma-separated case IDs | all cases |
| `--checkpoint-every-cases` | Rewrite a complete checkpoint after N completed cases; `0` disables | `2000` |

Examples:

```bash
fmfsolver-cli -i cases.csv --cases mode_a,mode_b -j 2
newtsolver-cli -i cases.xlsx -o results.csv --cases baseline -j 1
```

Selected rows retain input-table order. Unknown case IDs reject the request.
`--cases` requires at least one value. Successful execution writes `[RUN]` and
`[OK]` messages; validation and execution failures return a nonzero process exit.

Output-path validation rejects collisions with the input table, any STL, and
any planned VTP before execution. See [Outputs](outputs.md) and
[Shielding and parallel execution](shielding-and-parallel.md).
