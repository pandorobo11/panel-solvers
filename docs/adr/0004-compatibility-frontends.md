# ADR 0004: Preserve legacy interfaces with thin frontends

- Status: Accepted
- Date: 2026-08-12

## Context

Users and automation may rely on two command families, package imports, input
schemas, outputs, and GUI entry points. Requiring an immediate switch to a single
new interface would combine architecture migration with a breaking product
migration.

## Decision

Reserve `src/fmfsolver` and `src/newtsolver` for thin compatibility frontends.
They may translate legacy input and select shared application/model
configuration, but cannot implement new numerical, artifact, caching, execution,
or GUI behavior. Preserve old commands through the compatibility period. Any
deprecation/removal needs a separate accepted plan.

## Consequences

Legacy users can migrate independently of internal refactoring. Compatibility
tests become a first-class suite, and some forwarding code remains temporarily.
Phase 0 provides importable placeholders but does not falsely register nonworking
commands.
