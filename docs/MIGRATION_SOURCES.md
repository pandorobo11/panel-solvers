# Migration sources

These commits are the immutable baselines for the first migration pass.

| Legacy implementation | Repository | Baseline commit | Recorded local branch |
|---|---|---|---|
| fmfsolver | https://github.com/pandorobo11/fmfsolver | `b62bc844d02a8f5212e62a53dea3238a1414317d` | `main` |
| newtsolver | https://github.com/pandorobo11/newtsolver | `dc1357d0d50bbedfdc8b3429cab37e6b98b56c70` | `main` |

The commits were verified in the local sibling repositories on 2026-08-12
(Asia/Tokyo). Phase 1 must record any intentional replacement baseline before
generating golden data. Existing golden data must never be silently regenerated
from a newer commit.

Legacy checkouts are behavioral references, not architectural templates. During
an implementation task they are read-only. Differences between the two sources
must be captured in compatibility documentation, tests, or an ADR before being
resolved.
