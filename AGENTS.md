# Repository instructions

## Purpose and priorities

This repository is the neutral platform that will integrate `fmfsolver` and
`newtsolver`. Apply these priorities in order:

1. numerical correctness;
2. existing user compatibility;
3. architecture boundaries;
4. maintainability;
5. performance;
6. reduced code volume.

Never change numerical behavior or a public contract merely to remove duplicate
code.

## Read before editing

Before changing code, read:

- `docs/DEVELOPMENT.md`;
- `docs/ARCHITECTURE.md`;
- `docs/NUMERICAL_CONVENTIONS.md`;
- `docs/COMPATIBILITY.md`;
- `docs/MIGRATION_PLAN.md`;
- ADRs related to the target area;
- the current issue or task.

## Legacy references

The legacy implementations are read-only references. Their authoritative URLs
and commits are in `docs/MIGRATION_SOURCES.md`. Local checkouts may live at
`.reference/fmfsolver`, `.reference/newtsolver`, or the workspace sibling paths.
Do not edit them during migration work. If the implementations differ, report
both behaviors and their effects; do not silently select one.

## Dependency direction

Allowed high-level dependencies are:

- `app -> models -> core`;
- `app -> core`;
- compatibility frontends (`fmfsolver`, `newtsolver`) -> `app/models/core`.

Prohibited:

- `core` importing `models`, `app`, GUI, or a compatibility frontend;
- `models` importing `app`, GUI, or a compatibility frontend;
- physical equations in GUI code;
- new business or numerical logic in a compatibility frontend.

Keep `src/fmfsolver` and `src/newtsolver` as thin compatibility frontends.

## Model boundary

The common model contract must represent each panel's local nondimensional load
vector, visualization scalars, and model metadata. It must not reduce every model
to pressure coefficient alone, because that would discard Sentman tangential
loads. The common engine owns area/reference normalization and force/moment
integration.

## Numerical rules

- Use SI internally.
- Make degree versus radian explicit in names or types.
- Make coordinate frames explicit with suffixes such as `_stl`, `_body`, and
  `_wind`.
- Store per-panel vectors as `(n_faces, 3)` unless an approved ADR says otherwise.
- Validate shapes where NumPy broadcasting is used.
- Handle NaN, infinity, degenerate faces, and zero reference quantities
  explicitly.
- Do not change signs, axes, or normalization conventions without an accepted ADR
  and compatibility plan.
- Never mix a numerical-formula change with a structural migration PR.

## Regression and compatibility

Do not update expected coefficients, panel loads, shielding masks, CSV columns,
VTP/NPZ fields, or case signatures without documenting the intended change,
evidence, effect, and tolerance. Compare VTP/NPZ semantic arrays and metadata, not
file bytes. Public API changes require compatibility tests and migration notes.

## Change discipline

- Keep one issue to one independently reviewable change.
- Edit only the files needed for the task.
- Do not include unrelated cleanup, renaming, or formatting.
- Explain every new production dependency.
- Do not push directly to `main`, rewrite history, or merge on behalf of the user
  unless explicitly requested.
- If code, tests, literature, and ADRs disagree about numerical behavior, stop
  that decision and report the conflict.

## Verification

Run the standard checks:

```bash
uv sync --locked --extra rayaccel
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run ruff check src tests scripts
uv build
```

As applicable, also test the changed CLI's `--help`, the built wheel, the GUI,
Embree and rtree backends, and model-specific golden regressions.

## Completion report

Report changed files, implemented behavior, design choices, checks and results,
numeric differences, compatibility impact, remaining risks, and cautions for the
next migration phase.

## Review priorities

Review numerical formulas, units, signs, coordinate frames, shapes/broadcasting,
compatibility, cache/signature keys, worker failure/cancellation, mesh normals and
degenerate faces, output completeness, and missing regression coverage before
style concerns.
