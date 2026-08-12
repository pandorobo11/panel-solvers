# GUI tests

Shared GUI, viewer, case selection, and lifecycle tests belong here. They use
injected non-OpenGL plotters and deterministic execution adapters so they remain
separable from headless numerical tests and run on every CI platform.

The pinned GUI-visible legacy behavior and known product differences are
inventoried in `docs/phase1/BEHAVIORAL_INVENTORY.md` and
`docs/phase1/LEGACY_DIFFERENCES.md`. Platform-dependent screenshots are not Phase
1 goldens.
