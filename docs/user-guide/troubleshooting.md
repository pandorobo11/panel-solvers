# Troubleshooting

## An STL cannot be found

Relative STL paths are resolved from the input table's directory. Check the path
from that directory and use semicolons only between complete component paths.

## The input table is rejected

Use the reported spreadsheet row and field. Common causes are a missing required
header, a non-finite value, a non-positive reference quantity, an incomplete FMF
Mode A/B pair, an invalid equation selector, or an attitude outside the reader
domain. See the solver-specific input reference.

## Embree is unavailable

Install the optional extra with `python -m pip install '.[rayaccel]'`, or set the
case's `ray_backend` to `rtree`. An explicit `embree` request intentionally does
not fall back.

## The result path is rejected

The summary may not alias the input file, an STL, or any planned VTP path.
Choose a distinct filename and directory. Collision checks are deliberately
portable across case-insensitive Windows and common macOS filesystems.

## A VTP does not load automatically

Confirm that `save_vtp_on=1`, that the file is under the resolved `out_dir`, and
that it was generated for the selected case. Automatic loading requires the case
ID and an accepted current or legacy signature to match.

## A canceled run does not stop immediately

Cancellation is observed between cases. A currently executing ray query or
physical-model solve is allowed to finish. Treat artifacts from failed or
canceled runs as partial state.

## Legacy imports or versions are surprising

The installed distribution is `panel-solvers`, while the compatibility package
versions remain FMF `1.3.8` and newtsolver `1.0.3`. Do not install the shared and
legacy distributions together. Direct Python implementation details are best
effort; use documented CLI, GUI, and file interfaces for stable automation.
