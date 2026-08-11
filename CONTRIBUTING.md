# Contributing

This migration prioritizes numerical correctness and compatibility over code
deduplication. Read `AGENTS.md`, `docs/DEVELOPMENT.md`, the relevant ADRs, and the
current migration issue before starting.

## Change scope

- Use one issue, one branch or worktree, and one pull request for each reviewable
  migration step.
- Do not combine physical-equation changes with structural refactoring.
- Do not silently choose one legacy behavior when the implementations disagree.
- Keep changes minimal; avoid unrelated renames and formatting.
- Do not directly push or merge to `main` as part of an implementation task.

## Required checks

```bash
uv sync --locked --extra rayaccel
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run ruff check src tests scripts
uv build
```

Changes to installed interfaces also require a built-wheel smoke test. Changes
to a physical model, shielding, geometry, integration, caching, or signatures
require the applicable golden regression suite and a report of observed numeric
differences.

## Pull request description

Include:

1. the migration issue and scope;
2. design choices and relevant ADRs;
3. commands run and results;
4. numerical deltas and tolerances, or an explicit statement that no numerical
   code changed;
5. compatibility impact;
6. remaining risks and follow-up work.

Golden data must identify the legacy repository and commit that generated it.
Updating expected values merely to make tests pass is prohibited.
