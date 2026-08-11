# Compatibility tests

Tests for legacy Python APIs, commands, CSV schemas, and VTP/NPZ metadata belong
here. They are added as each compatibility surface migrates. Phase 1 records the
unimplemented source contracts in `tests/fixtures/phase1/golden/*/contracts.json`
and `docs/phase1/BEHAVIORAL_INVENTORY.md`; compatibility tests should consume
those records as frontends are introduced rather than re-reading mutable legacy
HEADs.
