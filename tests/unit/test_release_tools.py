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
    create_release_archives,
    expected_tag,
    hypothetical_next_version,
    release_notes,
    select_built_sdist,
    select_built_wheel,
    sha256_file,
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
        examples = repository / "examples"
        for relative, content in (
            ("README.md", "# Examples\n\nRun both command examples.\n"),
            ("fmfsolver/basic.csv", "case_id,stl_path\nf,../geometry/plate.stl\n"),
            ("newtsolver/basic.csv", "case_id,stl_path\nn,../geometry/plate.stl\n"),
            ("geometry/plate.stl", "solid plate\nendsolid plate\n"),
        ):
            path = examples / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        docs_site = repository / ".hatch-build" / "panel-solvers-docs-site"
        (docs_site / "solvers").mkdir(parents=True)
        for relative in (
            "index.html",
            "solvers/fmfsolver.html",
            "solvers/newtsolver.html",
        ):
            (docs_site / relative).write_text(relative, encoding="utf-8")
        return repository

    def write_release_archives(self, repository: Path) -> tuple[Path, Path]:
        return create_release_archives(
            repository,
            docs_site_dir=(
                repository / ".hatch-build" / "panel-solvers-docs-site"
            ),
        )

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
            docs_site = (
                repository / ".hatch-build" / "panel-solvers-docs-site"
            )
            for page in (
                "index.html",
                "solvers/fmfsolver.html",
                "solvers/newtsolver.html",
            ):
                archive.writestr(
                    f"panelsolver/_docs_site/{page}",
                    (docs_site / page).read_bytes(),
                )
        return wheel

    def write_sdist(
        self,
        repository: Path,
        *,
        filename: str = "panel_solvers-2.3.4.tar.gz",
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
            ("version", "panel-solvers", "2.3.5"),
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
            self.write_release_archives(repository)
            manifest_path = repository / "dist" / "manifest.json"
            commit = "a" * 40

            manifest = create_dist_manifest(
                repository,
                commit,
                manifest_path,
            )

            self.assertEqual(commit, manifest["github_commit_sha"])
            artifacts = {item["kind"]: item for item in manifest["artifacts"]}
            self.assertEqual(wheel.name, artifacts["wheel"]["filename"])
            self.assertEqual(sdist.name, artifacts["sdist"]["filename"])
            self.assertEqual(2, manifest["schema"]["version"])
            self.assertEqual(
                manifest,
                verify_dist_manifest(
                    repository,
                    manifest_path,
                    expected_commit=commit,
                ),
            )

    def test_manifest_rejects_distribution_hash_tampering(self) -> None:
        for field in ("wheel", "sdist", "docs_zip", "examples_zip"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                wheel = self.write_wheel(repository)
                sdist = self.write_sdist(repository)
                docs_zip, examples_zip = self.write_release_archives(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "b" * 40, manifest_path)

                target = {
                    "wheel": wheel,
                    "sdist": sdist,
                    "docs_zip": docs_zip,
                    "examples_zip": examples_zip,
                }[field]
                with target.open("ab") as stream:
                    stream.write(b"tampered")

                with self.assertRaisesRegex(RuntimeError, rf"{field} hash mismatch"):
                    verify_dist_manifest(repository, manifest_path)

    def test_manifest_rejects_checkout_commit_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_sdist(repository)
            self.write_release_archives(repository)
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
                self.write_release_archives(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "e" * 40, manifest_path)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["artifacts"][0]["metadata"][field] = value
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                with self.assertRaisesRegex(RuntimeError, "wheel METADATA mismatch"):
                    verify_dist_manifest(repository, manifest_path)

    def test_release_archives_are_deterministic_and_have_expected_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            outputs = repository / "examples" / "fmfsolver" / "outputs"
            outputs.mkdir()
            (outputs / "ignored.csv").write_text("generated", encoding="utf-8")
            first_docs, first_examples = self.write_release_archives(repository)
            first_hashes = (sha256_file(first_docs), sha256_file(first_examples))
            second_docs, second_examples = self.write_release_archives(repository)
            self.assertEqual(
                first_hashes,
                (sha256_file(second_docs), sha256_file(second_examples)),
            )
            with zipfile.ZipFile(second_docs) as archive:
                self.assertIn("index.html", archive.namelist())
            with zipfile.ZipFile(second_examples) as archive:
                names = archive.namelist()
                self.assertIn("examples/README.md", names)
                self.assertIn("examples/fmfsolver/basic.csv", names)
                self.assertIn("examples/newtsolver/basic.csv", names)
                self.assertIn("examples/geometry/plate.stl", names)
                self.assertFalse(any("outputs" in name for name in names))

    def test_manifest_rejects_missing_extra_duplicate_and_filename_tampering(self) -> None:
        scenarios = ("missing", "extra", "duplicate", "filename")
        for scenario in scenarios:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.write_wheel(repository)
                self.write_sdist(repository)
                self.write_release_archives(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "f" * 40, manifest_path)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if scenario == "missing":
                    (repository / "dist" / manifest["artifacts"][2]["filename"]).unlink()
                elif scenario == "extra":
                    (repository / "dist" / "unexpected.bin").write_bytes(b"extra")
                elif scenario == "duplicate":
                    manifest["artifacts"][3] = dict(manifest["artifacts"][2])
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                else:
                    manifest["artifacts"][2]["filename"] = "renamed-docs.zip"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    verify_dist_manifest(repository, manifest_path)

    def test_distribution_selection_requires_exactly_one_wheel_and_sdist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_sdist(repository)
            self.assertEqual(
                "panel_solvers-2.3.4.tar.gz",
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
                'version = 1\n\n[[package]]\nname = "panel-solvers"\n'
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
