import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.probe_legacy_rollback import (
    LEGACY_SPECS,
    _archive_commit,
    sha256_file,
)

ROOT = Path(__file__).parents[2]


class LegacyRollbackProbeTests(unittest.TestCase):
    def test_pins_match_migration_sources(self) -> None:
        migration_sources = (ROOT / "docs" / "MIGRATION_SOURCES.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            {"fmfsolver", "newtsolver"},
            {spec.name for spec in LEGACY_SPECS},
        )
        for spec in LEGACY_SPECS:
            with self.subTest(product=spec.name):
                self.assertIn(spec.repository.removesuffix(".git"), migration_sources)
                self.assertIn(spec.commit, migration_sources)

    def test_sha256_is_content_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.whl"
            path.write_bytes(b"first")
            first = sha256_file(path)
            path.write_bytes(b"second")
            self.assertNotEqual(first, sha256_file(path))

    def test_archive_refuses_a_commit_other_than_the_exact_pin(self) -> None:
        spec = LEGACY_SPECS[0]
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "scripts.probe_legacy_rollback._git",
            return_value="0" * 40,
        ), self.assertRaisesRegex(RuntimeError, "commit mismatch"):
            _archive_commit(
                Path(temp_dir),
                spec,
                Path(temp_dir) / "archive",
            )


if __name__ == "__main__":
    unittest.main()
