# Test fixtures

Small, reviewable source meshes, cases, and golden artifacts belong here. Every
golden fixture must identify its source repository, commit, command, and numeric
tolerance.

`phase1/` contains the pinned legacy behavior matrix, provenance manifest, tiny
source meshes, valid/invalid case tables, and semantic JSON captures. See
`phase1/README.md` before regenerating it.

The pinned legacy repositories and these carried-forward fixtures were created
by the same maintainer as panel-solvers. The fixtures are historical migration
evidence, not unidentified third-party assets, and are distributed under the
project's Apache-2.0 terms.

Current-schema case tables are derived in temporary directories by
`tests/current_case_fixtures.py`; the committed Phase 1 inputs remain unchanged.
