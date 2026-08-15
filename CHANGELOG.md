# Changelog

This file is the source of truth for `panel-solvers` release notes. Legacy
migration baselines and runtime artifact version semantics are recorded in ADR
0007 and ADR 0012.

## [Unreleased]

- Change Summary CSV and VTP `solver_version` provenance to the installed
  `panel-solvers` distribution version for both FMF and Hypersonic. The legacy
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
  `panel-solvers[rayaccel]` distribution extra.
- Reject portable summary and planned-artifact path collisions after Unicode NFC
  normalization and casefolding, including existing symlink and hardlink aliases.
- Completed Phase 8 supported-domain compatibility remediation, final-candidate
  audit, release/rollback hardening, and durable acceptance reporting.
