import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.release_tools import (
    create_dist_manifest,
    expected_tag,
    hypothetical_next_version,
    release_notes,
    select_built_sdist,
    select_built_wheel,
    verify_dist_manifest,
    verify_lock_version,
    verify_release_tag,
    verify_tag,
)
from scripts.smoke_installed_wheel import _smoke_subprocess_environment


class ReleaseToolTests(unittest.TestCase):
    def make_repository(self, root: Path, *, version: str = "2.3.4") -> Path:
        repository = root / "repository"
        repository.mkdir()
        (repository / "pyproject.toml").write_text(
            "[project]\nname = \"panelsolver\"\n"
            f'version = "{version}"\n',
            encoding="utf-8",
        )
        (repository / "uv.lock").write_text(
            'version = 1\n\n[[package]]\nname = "panelsolver"\n'
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
        name: str = "panelsolver",
        version: str = "2.3.4",
        filename: str | None = None,
    ) -> Path:
        dist = repository / "dist"
        dist.mkdir(exist_ok=True)
        wheel = dist / (filename or f"panelsolver-{version}-py3-none-any.whl")
        metadata_path = f"panelsolver-{version}.dist-info/METADATA"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                metadata_path,
                f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n",
            )
        return wheel

    def write_sdist(
        self,
        repository: Path,
        *,
        filename: str = "panelsolver-2.3.4.tar.gz",
        content: bytes = b"sdist",
    ) -> Path:
        dist = repository / "dist"
        dist.mkdir(exist_ok=True)
        sdist = dist / filename
        sdist.write_bytes(content)
        return sdist

    def git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def make_git_repository(self, root: Path) -> Path:
        repository = self.make_repository(root)
        self.git(repository, "init")
        self.git(repository, "config", "user.name", "Release Test")
        self.git(repository, "config", "user.email", "release@example.invalid")
        self.git(repository, "add", ".")
        self.git(repository, "commit", "-m", "release candidate")
        self.git(repository, "branch", "-M", "main")
        return repository

    def set_origin_main(self, repository: Path, commit: str) -> None:
        self.git(repository, "update-ref", "refs/remotes/origin/main", commit)

    def commit_file(self, repository: Path, path: str, content: str) -> str:
        (repository / path).write_text(content, encoding="utf-8")
        self.git(repository, "add", path)
        self.git(repository, "commit", "-m", f"update {path}")
        return self.git(repository, "rev-parse", "HEAD")

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
            ("version", "panelsolver", "2.3.5"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.write_wheel(repository, name=name, version=version)
                with self.assertRaisesRegex(RuntimeError, f"wheel {field} mismatch"):
                    select_built_wheel(repository)

    def test_manifest_generation_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            wheel = self.write_wheel(repository)
            sdist = self.write_sdist(repository)
            manifest_path = repository / "dist" / "manifest.json"
            commit = "a" * 40

            manifest = create_dist_manifest(
                repository,
                commit,
                manifest_path,
            )

            self.assertEqual(
                {"name": "panelsolver.dist-manifest", "version": 1},
                manifest["schema"],
            )
            self.assertEqual(commit, manifest["github_commit_sha"])
            self.assertEqual(wheel.name, manifest["wheel"]["filename"])
            self.assertEqual(
                {"name": "panelsolver", "version": "2.3.4"},
                manifest["wheel"]["metadata"],
            )
            self.assertEqual(sdist.name, manifest["sdist"]["filename"])
            self.assertEqual(
                manifest,
                verify_dist_manifest(
                    repository,
                    manifest_path,
                    expected_commit=commit,
                ),
            )

    def test_manifest_rejects_distribution_hash_tampering(self) -> None:
        for field in ("wheel", "sdist"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                wheel = self.write_wheel(repository)
                sdist = self.write_sdist(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "b" * 40, manifest_path)

                target = wheel if field == "wheel" else sdist
                with target.open("ab") as stream:
                    stream.write(b"tampered")

                with self.assertRaisesRegex(RuntimeError, rf"{field} hash mismatch"):
                    verify_dist_manifest(repository, manifest_path)

    def test_manifest_rejects_checkout_commit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_sdist(repository)
            manifest_path = repository / "dist" / "manifest.json"
            create_dist_manifest(repository, "c" * 40, manifest_path)

            with self.assertRaisesRegex(RuntimeError, "manifest commit mismatch"):
                verify_dist_manifest(
                    repository,
                    manifest_path,
                    expected_commit="d" * 40,
                )

    def test_manifest_rejects_wheel_metadata_mismatch(self) -> None:
        for field, value in (("name", "different"), ("version", "9.9.9")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.write_wheel(repository)
                self.write_sdist(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "e" * 40, manifest_path)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["wheel"]["metadata"][field] = value
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                with self.assertRaisesRegex(RuntimeError, "wheel METADATA mismatch"):
                    verify_dist_manifest(repository, manifest_path)

    def test_distribution_selection_requires_exactly_one_wheel_and_sdist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_sdist(repository)
            self.assertEqual(
                "panelsolver-2.3.4.tar.gz",
                select_built_sdist(repository).name,
            )
            self.write_sdist(repository, filename="duplicate.tar.gz")
            with self.assertRaisesRegex(RuntimeError, "exactly one sdist"):
                select_built_sdist(repository)

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

    def test_annotated_tag_matches_expected_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            expected_commit = self.git(repository, "rev-parse", "HEAD")
            self.set_origin_main(repository, expected_commit)
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "release 2.3.4")

            self.assertEqual(
                expected_commit,
                verify_release_tag(
                    repository,
                    "v2.3.4",
                    "refs/remotes/origin/main",
                ),
            )
            self.git(repository, "checkout", "--detach", "v2.3.4")
            self.assertEqual(
                expected_commit,
                verify_release_tag(
                    repository,
                    "v2.3.4",
                    "refs/remotes/origin/main",
                ),
            )

    def test_lightweight_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "v2.3.4")

            with self.assertRaisesRegex(RuntimeError, "must be annotated"):
                verify_release_tag(repository, "v2.3.4")

    def test_version_mismatched_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "-a", "v2.3.5", "-m", "wrong version")

            with self.assertRaisesRegex(RuntimeError, "tag/version mismatch"):
                verify_release_tag(repository, "v2.3.5")

    def test_annotated_tag_on_old_main_commit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "wrong target")
            expected_commit = self.commit_file(
                repository,
                "candidate.txt",
                "intended release commit\n",
            )
            self.set_origin_main(repository, expected_commit)

            with self.assertRaisesRegex(RuntimeError, "tag target mismatch"):
                verify_release_tag(
                    repository,
                    "v2.3.4",
                    "refs/remotes/origin/main",
                )

    def test_annotated_tag_on_side_branch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            main_commit = self.git(repository, "rev-parse", "main")
            self.set_origin_main(repository, main_commit)
            self.git(repository, "checkout", "-b", "side")
            self.commit_file(repository, "side.txt", "side branch\n")
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "side target")

            with self.assertRaisesRegex(RuntimeError, "tag target mismatch"):
                verify_release_tag(
                    repository,
                    "v2.3.4",
                    "refs/remotes/origin/main",
                )

    def test_release_tag_requires_nonempty_changelog_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.commit_file(
                repository,
                "CHANGELOG.md",
                "# Changelog\n\n## [Unreleased]\n\n- Later.\n",
            )
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "no notes")

            with self.assertRaisesRegex(RuntimeError, "no release section"):
                verify_release_tag(repository, "v2.3.4")

    def test_release_tag_requires_matching_lock_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.commit_file(
                repository,
                "uv.lock",
                'version = 1\n\n[[package]]\nname = "panelsolver"\n'
                'version = "2.3.5"\n',
            )
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "wrong lock")

            with self.assertRaisesRegex(RuntimeError, "uv.lock.*mismatch"):
                verify_release_tag(repository, "v2.3.4")

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
