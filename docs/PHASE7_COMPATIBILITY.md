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
  inputs: when a later case raises a caught Python exception, FMF forwards worker
  logs and discards completed results from that chunk, while newtsolver drops
  worker logs and yields those completed results before reporting the error;
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

## Case input and artifact identity

The compatibility readers keep separate FMF and newtsolver schemas, defaults,
validation callbacks, and error wording over one table-reading mechanism. Rows
are adapted to `CaseExecutionRequest` through product policies that select the
model, mesh validation rule, legacy environment prefix, and attitude domain.

The ADR 0005 execution signature is prepared through the same mesh and
shielding-resolution path used by execution, without evaluating physical panel
loads. Ordered pinned legacy hashes remain product-owned fallback identities.
They use the frozen `1.3.8` and `1.0.3` compatibility versions and are neither
interpreted by core nor treated as interchangeable with the primary signature.

## Execution, serialization, and GUI adapters

The shared runtime executes adapted requests serially or through the Phase 5
spawn scheduler. FMF selects `FORWARD`/`DISCARD_CHUNK`; newtsolver selects
`DROP`/`YIELD_COMPLETED`. Phase 8 independently found that the original Phase 7
policy wiring and documentation had the partial-result choices reversed, then
restored the pinned same-chunk failure behavior without changing successful
results. Shielding reuse may change execution order, but every
checkpoint and final summary is reconstructed in input order. Cancellation is
observed at case boundaries and worker failures retain their remote traceback.

Each complete case projects and writes VTP/NPZ according to its flags, including
the retained output-directory side effect when both flags are off. Summary CSV
snapshots use the existing product schemas and D010 atomic-write policies. FMF
adds only `mode`, resolved `S`/`Ti_K`, and its NPZ physical values; newtsolver
adds only its canonical equation VTP metadata. Both artifacts and CSV carry the
primary ADR 0005 signature and frozen product-facing version.

Both default GUI specifications now contain real readers, signature builders,
execution, collision validation, and wind-direction adapters. The non-calculating
fallback remains only for an explicitly adapter-free specification and is not
used by either normal product launcher.

## Commands and CLI behavior

The distribution registers both GUI aliases and the batch command for each
product. The two batch entry modules select one shared CLI flow while retaining
their exact frozen program name, description, help wrapping, D008 `--cases`
cardinality, and D009 collision behavior. Case selection remains comma/space
aware and input ordered; invalid parser values exit 2, while reader, solver, and
worker exceptions remain uncaught command failures. Checkpoints rewrite the
complete successful snapshot and final output uses the same product-selected
atomic CSV policy.

CI builds and reinstalls the wheel on Ubuntu, Windows, and macOS, verifies all
six entry-point targets, compares both CLI help texts exactly, and runs both
unchanged Phase 1 input tables from a temporary directory outside the checkout.

## Python compatibility surface

The complete Phase 1 module inventories now import from the unified
distribution. Compatibility modules translate legacy DataFrame, dictionary,
mutable-mesh, serializer, scheduler, and no-argument GUI constructor shapes to
shared implementations. The roots retain exact empty-list `__all__` values and
expose product-facing `__version__` values of `1.3.8` and `1.0.3` independently
of the `panel-solvers` distribution version.

FMF forwards its Sentman vector and US1976 helpers only. newtsolver retains the
exact ordered `panel_core.__all__` and `pressure_models.__all__` lists, including
the recorded underscore exports. It forwards the independent pressure-model,
selector, attitude, and panel-force helpers without adding them to FMF. Direct
solver calls return the pinned legacy signature while normal Phase 7 runtime
artifacts continue to carry the primary ADR 0005 identity and accept ordered
legacy identities as fallbacks.

Shared compatibility adapters own call-shape translation, mutable views of the
immutable mesh contract, DataFrame result reconstruction, and direct-array
serialization. The compatibility packages do not import NumPy, SciPy, trimesh,
or PyVista from their computational forwarding modules and contain no physical
formula, geometry, cache, shielding, scheduler, or serializer implementation.
Installed-wheel smoke testing imports every frozen module and checks the exact
root/version/D025 export contracts before exercising both command families.

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

**Status:** Complete. Issues #47–#52 and their dependent draft PRs passed the
listed gates and merged serially. `PHASE7_USER_GUIDE.md` is the user/release
handoff and `PHASE7_EXECUTION_RECORD.md` records the exact CI, installed-wheel,
numerical, and manual GUI evidence. Phase 8 remains not started.
