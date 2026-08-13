import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.release_tools import (
    expected_tag,
    hypothetical_next_version,
    release_notes,
    select_built_wheel,
    verify_lock_version,
    verify_tag,
)
from scripts.smoke_installed_wheel import _smoke_subprocess_environment


class ReleaseToolTests(unittest.TestCase):
    def make_repository(self, root: Path, *, version: str = "2.3.4") -> Path:
        repository = root / "repository"
        repository.mkdir()
        (repository / "pyproject.toml").write_text(
            "[project]\nname = \"panel-solvers\"\n"
            f'version = "{version}"\n',
            encoding="utf-8",
        )
        (repository / "uv.lock").write_text(
            'version = 1\n\n[[package]]\nname = "panel-solvers"\n'
            f'version = "{version}"\n',
            encoding="utf-8",
        )
        (repository / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n- Later.\n\n"
            f"## [{version}] - 2026-08-14\n\n- Released safely.\n",
            encoding="utf-8",
        )
        return repository

    def write_wheel(
        self,
        repository: Path,
        *,
        name: str = "panel-solvers",
        version: str = "2.3.4",
        filename: str | None = None,
    ) -> Path:
        dist = repository / "dist"
        dist.mkdir(exist_ok=True)
        wheel = dist / (filename or f"panel_solvers-{version}-py3-none-any.whl")
        metadata_path = f"panel_solvers-{version}.dist-info/METADATA"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                metadata_path,
                f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n",
            )
        return wheel

    def test_wheel_selection_is_version_independent_and_metadata_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            expected = self.write_wheel(repository)
            self.assertEqual(expected, select_built_wheel(repository))

            self.write_wheel(repository, filename="duplicate.whl")
            with self.assertRaisesRegex(RuntimeError, "exactly one wheel"):
                select_built_wheel(repository)

    def test_wheel_rejects_name_and_version_mismatch(self) -> None:
        for field, name, version in (
            ("name", "different", "2.3.4"),
            ("version", "panel-solvers", "2.3.5"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.write_wheel(repository, name=name, version=version)
                with self.assertRaisesRegex(RuntimeError, f"wheel {field} mismatch"):
                    select_built_wheel(repository)

    def test_lock_tag_and_changelog_form_one_release_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            verify_lock_version(repository, "2.3.4")
            self.assertEqual("v2.3.4", expected_tag("2.3.4"))
            self.assertEqual("2.3.5.dev0", hypothetical_next_version("2.3.4"))
            verify_tag("v2.3.4", "2.3.4")
            self.assertEqual("- Released safely.\n", release_notes(repository, "2.3.4"))
            with self.assertRaisesRegex(RuntimeError, "tag/version mismatch"):
                verify_tag("2.3.4", "2.3.4")
            with self.assertRaisesRegex(RuntimeError, "no release section"):
                release_notes(repository, "9.9.9")

    def test_smoke_environment_is_fixed_and_removes_product_tuning(self) -> None:
        inherited = {
            "COLUMNS": "140",
            "LINES": "60",
            "PANELSOLVER_SHIELD_BATCH_SIZE": "invalid",
            "FMFSOLVER_PARALLEL_CHUNK_CASES": "99",
            "NEWTSOLVER_SHIELD_CACHE_MAX": "4",
            "UNRELATED_SETTING": "preserved",
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ,
            inherited,
            clear=True,
        ):
            environment = _smoke_subprocess_environment(Path(temp_dir))
            self.assertEqual("80", environment["COLUMNS"])
            self.assertEqual("24", environment["LINES"])
            self.assertEqual("preserved", environment["UNRELATED_SETTING"])
            self.assertFalse(
                any(
                    name.startswith(
                        ("PANELSOLVER_", "FMFSOLVER_", "NEWTSOLVER_")
                    )
                    for name in environment
                )
            )
            for name in (
                "XDG_CACHE_HOME",
                "MPLCONFIGDIR",
                "PYVISTA_USERDATA_PATH",
                "LOCALAPPDATA",
            ):
                self.assertTrue(Path(environment[name]).is_dir())


if __name__ == "__main__":
    unittest.main()
