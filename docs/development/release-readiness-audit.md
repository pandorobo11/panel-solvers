# Initial-release metadata and dependency audit

This audit records technical evidence; it is not legal advice. It deliberately
does not choose a license without a primary source showing that the relevant
rightsholders granted one.

## Blocking licensing and provenance items

As of this foundation change, the `panel-solvers` root and the pinned FMF and
newtsolver source trees contain no `LICENSE`, `COPYING`, or `NOTICE` file. Their
`pyproject.toml` files also contain no license declaration. The shared project
therefore does not add speculative license metadata.

The initial public release is blocked until the maintainers document the rights
and required attribution for:

- code migrated from the pinned FMF and newtsolver repositories;
- the bundled US1976 atmosphere table and model constants;
- equations and explanatory material derived from cited technical reports;
- documentation, generated plots, example CSV files, and the sample STL.

Scientific citations on the solver pages identify technical sources but do not,
by themselves, grant a software or content license. Once ownership and grants
are confirmed, add the correct root license/notice files and corresponding
PEP 621 `project.license` metadata before publishing any artifact.

## Missing publication metadata

`pyproject.toml` currently has no authors or maintainers, no project URLs, and no
license metadata. These fields require maintainer-confirmed values and remain
first-release blockers rather than inferred data. The project name, static
version, description, README, Python requirement, dependencies, and six console
scripts are present.

## Runtime dependency observations

The direct runtime requirements correspond to imports or supported file/runtime
paths in the shared and compatibility packages: NumPy/SciPy, pandas and Excel
readers, Trimesh/rtree, NetworkX, PyVista/VTK integration, and PySide6. MkDocs is
development/build-only and is not a wheel runtime requirement.

Most runtime dependencies have neither lower nor upper bounds. This preserves
the migrated install contract but makes future upstream incompatibility less
predictable for a public wheel. PySide6 alone is exactly pinned to `6.9.3`; the
legacy projects carried the same pin, but no repository decision record explains
why that exact patch is uniquely required. Dependency bounds and the Qt pin
should be tested and documented in a follow-up change rather than broadly altered
in this release-foundation PR.

The declared Python range is `>=3.12`, while CI exercises Python 3.12 on Ubuntu,
Windows, and macOS. This proves the minimum only; the unbounded upper Python range
should be expanded in CI or constrained after compatibility testing before a
stable release.

## Release gate

Do not create the first public tag or GitHub Release until the license,
attribution/provenance, authors or maintainers, and project URL decisions above
are resolved and represented in the source distribution and wheel metadata.
