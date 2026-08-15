# Quickstart

The repository includes one small, runnable case for each solver. Both use the
shared mesh at `examples/geometry/plate.stl`; they are not regression fixtures.

## Run FMF

```bash
panelsolver fmf --input examples/fmfsolver/basic.csv --workers 1 --flush-every-cases 0
```

The compatibility form remains `fmfsolver-cli` with the same options.

This is a Sentman Mode A case using `S=5`, `Ti_K=300 K`, and `Tw_K=300 K`.
Its summary and VTP output are written to `examples/fmfsolver/outputs/`.

## Run newtsolver

```bash
panelsolver hypersonic --input examples/newtsolver/basic.csv --workers 1 --flush-every-cases 0
```

The compatibility form remains `newtsolver-cli` with the same options.

This is a `Mach=6`, `gamma=1.4` case. Omitted equation columns select the
defaults: Newtonian on windward panels and zero pressure (`shield`) on leeward
panels. Its outputs are written to `examples/newtsolver/outputs/`.

## Use the GUI

Launch the matching application:

```bash
fmfsolver-gui
newtsolver-gui
```

Select the corresponding `basic.csv`, select its row, and choose **Run Selected
Cases**. The GUI displays the generated VTP when one is saved. The plain
`fmfsolver` and `newtsolver` commands are GUI aliases.

## What was written

By default, the CLI writes:

- `outputs/basic_result.csv`: summary coefficient rows;
- `outputs/<case_id>.vtp`: mesh, panel scalars, and case metadata.

See [Outputs](../user-guide/outputs.md) for semantics and
[Case files](../user-guide/case-files.md) before editing the examples.

## Try the feature examples next

After the basic run, try `flow_modes.csv`, `shielding.csv`, `components.csv`,
or `attitude_modes.csv` under `examples/fmfsolver/`. The matching newtsolver
directory provides `pressure_models.csv`, `shielding.csv`, `components.csv`,
and `attitude_modes.csv`. Run each with the same CLI command pattern, replacing
the input path. Commands, expected relationships, GUI files, and output
locations are collected in the repository-level `examples/README.md`.
