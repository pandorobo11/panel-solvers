# CLI guide

The two batch commands share the same options:

```text
fmfsolver-cli --input PATH [--output PATH] [--workers N]
              [--cases ID [ID ...]] [--flush-every-cases N]
newtsolver-cli --input PATH [--output PATH] [--workers N]
               [--cases ID [ID ...]] [--flush-every-cases N]
```

| Option | Meaning | Default |
|---|---|---|
| `-i`, `--input` | CSV/XLSX/XLSM case table | required |
| `-o`, `--output` | Summary CSV | `<input_dir>/outputs/<input_stem>_result.csv` |
| `-j`, `--workers` | Spawn workers; must be at least 1 | `1` |
| `--cases` | Space- or comma-separated case IDs | all cases |
| `--flush-every-cases` | Rewrite a complete checkpoint after N completed cases; `0` disables | `100` |

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
