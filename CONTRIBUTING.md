# Contributing

This project prioritizes numerical correctness and compatibility over code
deduplication. Read `AGENTS.md`,
`docs/development/setup-and-testing.md`, the relevant ADRs, and the current issue
before starting.

## Change scope

- Keep one independently reviewable concern per branch/worktree and pull request.
- Do not combine physical-equation changes with structural refactoring.
- Do not silently resolve a supported numerical or file-contract conflict.
- Keep changes minimal and avoid unrelated renames or formatting.
- Do not push directly to or merge `main` as part of an implementation task.

## Required checks

```bash
uv sync --locked --extra rayaccel
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run ruff check src tests scripts
uv build
```

Installed-interface changes also require a built-wheel smoke test. Changes to a
physical model, shielding, geometry, integration, caching, or signatures require
the applicable golden regression suite and a report of observed numeric
differences.

## Pull request description

Include:

1. issue and scope;
2. design choices and relevant ADRs;
3. commands run and results;
4. numerical deltas and tolerances, or an explicit statement that no numerical
   code changed;
5. compatibility impact;
6. remaining risks and follow-up work.

Golden data must identify the pinned legacy repository and commit that generated
it. Updating expected values merely to make tests pass is prohibited. The
current workflow is in
[Development setup and testing](docs/development/setup-and-testing.md).

## Contribution license

Unless you explicitly state otherwise, contributions intentionally submitted
for inclusion in panel-solvers are provided under the project's
[Apache License 2.0](LICENSE), consistent with section 5 of that license. This
project does not require a Contributor License Agreement.
