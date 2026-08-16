# Changelog

This file is the source of truth for `panelsolver` release notes. Legacy
migration baselines and runtime artifact version semantics are recorded in ADR
0007 and ADR 0012.

## [Unreleased]

- Add the first-release foundation: strict offline documentation bundled in the
  wheel, shared GUI Help/About, deterministic documentation and examples ZIPs,
  manifest schema v2, and build-once release verification.
- Unify the canonical repository, distribution, package, and command namespace
  as `panelsolver`; the human-readable product name is Panel Solver. Preserve
  the `fmfsolver` and `newtsolver` packages and commands as legacy compatibility
  identities.
- Adopt the Apache License 2.0 for project-owned code, documentation, examples,
  and generated material; record author, maintainer, project URLs, PEP 639
  license metadata, and US1976/PDAS/dependency rights boundaries.
- Change Summary CSV and VTP `solver_version` provenance to the installed
  `panelsolver` distribution version for both FMF and Hypersonic. The legacy
  `fmfsolver 1.3.8` and `newtsolver 1.0.3` values remain migration baselines for
  legacy signatures and best-effort direct-Python compatibility; numerical
  results and case signatures are unchanged.
- Add canonical `panelsolver fmf` and `panelsolver hypersonic` batch selectors
  plus `panelsolver-gui fmf` and `panelsolver-gui hypersonic`, while retaining
  all six legacy compatibility commands. Add the small domain-specific
  `FMFCase`/`HypersonicCase` in-memory solve API at the package root; it writes
  no artifacts. Stable API case IDs now share portable NFC validation with case
  tables, and attitude resolution rejects non-text selectors and beta-sin
  alpha values outside the open principal interval.
- **Breaking:** Remove legacy Excel 97–2003 BIFF `.xls` input support and the
  `xlrd` runtime dependency. Convert `.xls` case files to `.xlsx` or CSV before
  using the current release. CSV, XLSX, and XLSM behavior is unchanged, and
  solver numerical results are unaffected.
- **Breaking:** Remove NPZ output, the `save_npz_on` case field, the Summary CSV
  `npz_path` column, and both compatibility frontends' `export_npz` API. Old
  case files must delete the `save_npz_on` column. Existing NPZ files are not
  automatically deleted; use VTP for visualization and panel data, and Summary
  CSV for aggregate results.
- Correct the optional ray-acceleration install hint to use the shared
  `panelsolver[rayaccel]` distribution extra.
- Reject portable summary and planned-artifact path collisions after Unicode NFC
  normalization and casefolding, including existing symlink and hardlink aliases.
- Completed Phase 8 supported-domain compatibility remediation, final-candidate
  audit, release/rollback hardening, and durable acceptance reporting.
