# GUI guide

## Offline help

Both launchers use the shared **Help** menu. **Documentation Home** opens the
root of the static site bundled in the installed wheel, while **This Solver**
opens the FMF or newtsolver page selected by the launcher's `SolverSpec`.
**About panel-solvers** shows the installed distribution version, the active
frontend compatibility version, and the product/model identity. If a packaged
page is unavailable, the GUI reports an error instead of terminating.

Launch the GUI for the physical model you intend to use:

```bash
fmfsolver-gui
newtsolver-gui
```

`fmfsolver` and `newtsolver` are equivalent GUI aliases.

## Run cases

1. Choose **Select Input File** and open a CSV, XLSX, XLSM, or XLS case table.
2. Select one or more table rows. With no selection, **Run Selected Cases** runs
   every loaded row.
3. Set **Workers**. Use `1` for the simplest deterministic run.
4. Choose **Run Selected Cases** and select the summary CSV destination.
5. Follow progress and diagnostics in the log panel.

Input validation issues are shown with spreadsheet row, case ID, field, and
message. The GUI uses the same reader, execution engine, checkpoint behavior,
and output serializers as the CLI.

## View and export

When a case saves VTP, the first selected case's result is loaded automatically. A
selected row also loads an existing `<out_dir>/<case_id>.vtp` when its case ID
and accepted signature match. The viewer can switch among available cell
scalars, adjust the camera and coloring, open another VTP, and save images.

Closing the window during a run requests cooperative cancellation and waits for
worker cleanup. An active ray query or model solve may finish before cancellation
is observed; files already written are not rolled back.

See [Case files](case-files.md), [Outputs](outputs.md), and
[Troubleshooting](troubleshooting.md).
