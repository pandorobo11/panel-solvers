# Changelog

This file is the source of truth for `panel-solvers` release notes. Product
compatibility versions are tracked separately under ADR 0007.

## [Unreleased]

- Correct the optional ray-acceleration install hint to use the shared
  `panel-solvers[rayaccel]` distribution extra, and document that current
  solver-generated NPZ outputs can be loaded with pickle disabled.
- Reject portable summary and planned-artifact path collisions after Unicode NFC
  normalization and casefolding, including existing symlink and hardlink aliases.
- Completed Phase 8 supported-domain compatibility remediation, final-candidate
  audit, release/rollback hardening, and durable acceptance reporting.
