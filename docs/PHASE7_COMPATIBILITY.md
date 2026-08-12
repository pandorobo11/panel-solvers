# Phase 7 packaging and public compatibility

Phase 7 turns the accepted shared engine and GUI into the two runnable legacy
product surfaces. It preserves numerical behavior and each product's public
contract while removing duplicated common implementation from the compatibility
packages. It does not perform the independent Phase 8 audit or archive either
legacy repository.

## Dependency sequence

Implementation is serialized through one issue, one worktree, and one draft PR
per slice:

1. #47 decides the single-distribution and compatibility-version mechanics;
2. #48 adds product case readers, attitude adaptation, and primary/legacy
   signature candidates;
3. #49 composes shared execution, CSV/VTP/NPZ serialization, and real GUI
   adapters;
4. #50 registers all six commands and preserves the two CLI contracts;
5. #51 forwards the frozen Python module and callable surfaces;
6. #52 completes user/release documentation, installed samples, both macOS GUI
   smokes, and Phase 7 acceptance.

Every slice starts from the latest accepted `origin/main`. It is made ready and
merged only after the complete unittest suite, unchanged Phase 1 goldens, Ruff,
build, and Ubuntu/Windows/macOS CI pass. Packaging slices additionally reinstall
and exercise the built wheel outside the repository.

## Distribution and versions

ADR 0007 selects one `panel-solvers` distribution containing all three packages
and both command families. Repository tags follow only `project.version`.

The frozen product-facing version values remain independent adapter contracts:

- FMF compatibility version: `1.3.8`;
- newtsolver compatibility version: `1.0.3`.

They remain visible only on legacy-compatible result, artifact, signature, and
Python surfaces. `importlib.metadata.version("panel-solvers")` reports the shared
distribution release. Canonical numerical signatures continue to use explicit
model and shielding algorithm versions, never an application version.

## Retained dual contracts

Phase 7 implements product policy rather than choosing a universal behavior:

- D004: FMF dispatches `.xls` to xlrd; newtsolver retains its openpyxl failure;
- D005/D006/D007: case IDs, duplicate comparison, and FMF-only `beta_tan`
  principal-angle rejection remain independent;
- D008: FMF `--cases` requires at least one value while newtsolver accepts none;
- D009/D010: collision scope and CSV temporary-file/durability policy remain
  product-selected;
- D015: worker logging and failure-partial policies remain explicit scheduler
  inputs;
- D017/D018: the ADR 0005 signature is primary and ordered legacy hashes remain
  opaque fallbacks, including distinct direct/file variants;
- D019/D020/D029: VTP, NPZ, and result CSV model fields remain separate;
- D022/D023/D024/D027: exact titles, close policies, and manual stale-artifact
  inspection remain as accepted in Phase 6;
- D025: the de facto Python surfaces are forwarded independently rather than
  replaced with a cross-product union.

ADR 0006 already preserves D011 mesh-repair policy. Phase 5 already defines the
neutral environment-variable precedence while retaining one explicitly selected
legacy prefix.

## Compatibility boundaries

Shared case mechanics, orchestration, serialization, CLI flow, and GUI behavior
belong in `panelsolver.app` or `panelsolver.core`. Physical equations remain in
the independent model packages. `fmfsolver` and `newtsolver` may define schemas,
policies, legacy signatures, and call-shape translation, but may not duplicate
common numerical or application implementation.

No existing command, field, module, or callable is deprecated in Phase 7. A
future removal needs its own accepted transition. The legacy repositories remain
read-only numerical references through Phase 8.

## Final acceptance evidence

Phase 7 can be marked complete only when:

- unchanged legacy samples run from a clean installed wheel;
- all six commands and exact CLI help contracts work on the installed wheel;
- the frozen module inventories and representative public calls work outside the
  source tree;
- CSV schemas/cells and semantic VTP/NPZ arrays/metadata match the Phase 1
  profiles without updated goldens or tolerances;
- both model paths pass on Ubuntu, Windows, and macOS with required Embree and
  supported rtree fallback coverage;
- both GUIs are manually smoked in the correct macOS user session, or any
  Computer Use visibility limitation is explicitly recorded as unverified with
  alternative evidence;
- numerical deltas, compatibility effects, remaining risks, release, and
  rollback instructions are documented.

These checks are migration acceptance, not the independent correctness,
architecture, performance, and lifecycle audit reserved for Phase 8.
