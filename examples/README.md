# Examples

These small cases are intended for first-time users and are independent of the
regression fixtures under `tests/fixtures`.

```bash
fmfsolver-cli --input examples/fmfsolver/basic.csv --workers 1 --flush-every-cases 0
newtsolver-cli --input examples/newtsolver/basic.csv --workers 1 --flush-every-cases 0
```

Both tables reference `geometry/plate.stl` through a path relative to the table.
Generated summary CSV and VTP files go into the solver example's `outputs/`
directory. See the [quickstart](../docs/getting-started/quickstart.md) before
extending a case.
