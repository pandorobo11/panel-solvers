from __future__ import annotations

import io
import json
import os
import subprocess
import tarfile
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
    is_prerelease,
    release_notes,
    select_built_sdist,
    select_built_wheel,
    sha256_file,
    verify_dist_manifest,
    verify_github_release_state,
    verify_lock_version,
    verify_release_tag,
    verify_tag,
    verify_wheel_contents,
    write_deterministic_zip,
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
        for name, content in (
            ("LICENSE", "license\n"),
            ("THIRD_PARTY_NOTICES.md", "notices\n"),
        ):
            (repository / name).write_text(content, encoding="utf-8")
        examples = repository / "examples"
        required = (
            "README.md",
            "fmf/basic.csv",
            "fmf/flow_modes.csv",
            "fmf/attitude_modes.csv",
            "fmf/shielding.csv",
            "hypersonic/basic.csv",
            "hypersonic/pressure_models.csv",
            "hypersonic/attitude_modes.csv",
            "hypersonic/shielding.csv",
            "geometry/plate.stl",
        )
        for relative in required:
            path = examples / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{relative}\n", encoding="utf-8")
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
        dist_info = f"panelsolver-{version}.dist-info"
        metadata = (
            "Metadata-Version: 2.4\n"
            f"Name: {name}\n"
            f"Version: {version}\n"
            "License-Expression: Apache-2.0\n"
            "Author: pandorobo11\n"
            "Project-URL: Repository, https://github.com/pandorobo11/panelsolver\n"
        )
        docs = {
            "index.html": b"home",
            "solvers/fmf.html": b"fmf",
            "solvers/hypersonic.html": b"hypersonic",
            "LICENSE": b"license\n",
            "THIRD_PARTY_NOTICES.md": b"notices\n",
        }
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(f"{dist_info}/METADATA", metadata)
            archive.writestr(f"{dist_info}/licenses/LICENSE", b"license\n")
            archive.writestr(
                f"{dist_info}/licenses/THIRD_PARTY_NOTICES.md",
                b"notices\n",
            )
            for relative, content in docs.items():
                archive.writestr(f"panelsolver/_docs_site/{relative}", content)
        return wheel

    def write_sdist(
        self,
        repository: Path,
        *,
        name: str = "panelsolver",
        version: str = "2.3.4",
        filename: str | None = None,
    ) -> Path:
        dist = repository / "dist"
        dist.mkdir(exist_ok=True)
        sdist = dist / (filename or f"panelsolver-{version}.tar.gz")
        payload = f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n".encode()
        with tarfile.open(sdist, "w:gz") as archive:
            info = tarfile.TarInfo(f"panelsolver-{version}/PKG-INFO")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        return sdist

    def prepare_artifacts(self, repository: Path) -> tuple[Path, Path, Path, Path]:
        wheel = self.write_wheel(repository)
        sdist = self.write_sdist(repository)
        docs, examples = create_release_archives(repository)
        return wheel, sdist, docs, examples

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

    def mutate_manifest(self, path: Path, callback) -> None:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        callback(manifest)
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_distribution_selection_uses_backend_filenames_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            wheel = self.write_wheel(repository, filename="backend-wheel.whl")
            sdist = self.write_sdist(repository, filename="backend-source.tar.gz")
            self.assertEqual(wheel, select_built_wheel(repository))
            self.assertEqual(sdist, select_built_sdist(repository))
            verify_wheel_contents(repository, wheel)

    def test_distribution_selection_rejects_duplicates_and_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_wheel(repository, filename="duplicate.whl")
            with self.assertRaisesRegex(RuntimeError, "exactly one wheel"):
                select_built_wheel(repository)
        for kind, name, version in (
            ("wheel", "different", "2.3.4"),
            ("wheel", "panelsolver", "2.3.5"),
            ("sdist", "different", "2.3.4"),
            ("sdist", "panelsolver", "2.3.5"),
        ):
            with self.subTest(kind=kind, name=name, version=version):
                with tempfile.TemporaryDirectory() as temp_dir:
                    repository = self.make_repository(Path(temp_dir))
                    writer = self.write_wheel if kind == "wheel" else self.write_sdist
                    writer(repository, name=name, version=version)
                    selector = select_built_wheel if kind == "wheel" else select_built_sdist
                    with self.assertRaisesRegex(RuntimeError, f"{kind} (name|version) mismatch"):
                        selector(repository)

    def test_release_archives_are_deterministic_and_current_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            self.write_wheel(repository)
            self.write_sdist(repository)
            excluded = repository / "examples" / "fmf" / "outputs" / "old.npz"
            excluded.parent.mkdir()
            excluded.write_bytes(b"old")
            (repository / "examples" / "hypersonic" / "old.xls").write_bytes(b"old")
            first = create_release_archives(repository)
            hashes1 = tuple(sha256_file(path) for path in first)
            second = create_release_archives(repository)
            hashes2 = tuple(sha256_file(path) for path in second)
            self.assertEqual(hashes1, hashes2)
            with zipfile.ZipFile(first[0]) as archive:
                self.assertEqual(b"home", archive.read("index.html"))
                self.assertIn("LICENSE", archive.namelist())
            with zipfile.ZipFile(first[1]) as archive:
                names = archive.namelist()
                self.assertIn("examples/fmf/flow_modes.csv", names)
                self.assertIn("examples/hypersonic/pressure_models.csv", names)
                self.assertFalse(any(name.endswith((".npz", ".xls")) for name in names))

    def test_manifest_v2_generation_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            wheel, sdist, docs, examples = self.prepare_artifacts(repository)
            manifest_path = repository / "dist" / "manifest.json"
            manifest = create_dist_manifest(repository, "a" * 40, manifest_path)
            self.assertEqual(
                {"name": "panelsolver.dist-manifest", "version": 2},
                manifest["schema"],
            )
            self.assertEqual(
                ["wheel", "sdist", "docs", "examples"],
                [item["kind"] for item in manifest["artifacts"]],
            )
            self.assertEqual(
                [wheel.name, sdist.name, docs.name, examples.name],
                [item["filename"] for item in manifest["artifacts"]],
            )
            self.assertEqual(
                manifest,
                verify_dist_manifest(repository, manifest_path, expected_commit="a" * 40),
            )

    def test_manifest_rejects_missing_extra_hash_and_commit_tampering(self) -> None:
        for case in ("missing", "extra", "hash", "commit"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                wheel, _sdist, docs, _examples = self.prepare_artifacts(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "b" * 40, manifest_path)
                if case == "missing":
                    docs.unlink()
                    expected = "file is missing"
                elif case == "extra":
                    (repository / "dist" / "extra.bin").write_bytes(b"extra")
                    expected = "artifact set mismatch"
                elif case == "hash":
                    with wheel.open("ab") as stream:
                        stream.write(b"tampered")
                    expected = "hash mismatch"
                else:
                    expected = "commit mismatch"
                with self.assertRaisesRegex(RuntimeError, expected):
                    verify_dist_manifest(
                        repository,
                        manifest_path,
                        expected_commit="c" * 40 if case == "commit" else None,
                    )

    def test_manifest_rejects_order_duplicate_kind_filename_and_unexpected_filename(self) -> None:
        for case in ("order", "kind", "duplicate_filename", "unexpected_filename"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.prepare_artifacts(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "d" * 40, manifest_path)
                if case == "order":
                    self.mutate_manifest(manifest_path, lambda value: value["artifacts"].reverse())
                    expected = "kinds/order mismatch"
                elif case == "kind":
                    self.mutate_manifest(
                        manifest_path,
                        lambda value: value["artifacts"][2].update(kind="wheel"),
                    )
                    expected = "kinds/order mismatch"
                elif case == "duplicate_filename":
                    def duplicate(value):
                        value["artifacts"][3]["filename"] = value["artifacts"][2]["filename"]
                        value["artifacts"][3]["sha256"] = value["artifacts"][2]["sha256"]

                    self.mutate_manifest(manifest_path, duplicate)
                    expected = "filenames must be unique"
                else:
                    source = repository / "dist" / "panelsolver-docs-v2.3.4.zip"
                    renamed = repository / "dist" / "renamed-docs.zip"
                    source.rename(renamed)

                    def rename(value, renamed_path=renamed):
                        value["artifacts"][2]["filename"] = renamed_path.name
                        value["artifacts"][2]["sha256"] = sha256_file(renamed_path)

                    self.mutate_manifest(manifest_path, rename)
                    expected = "filename does not match"
                with self.assertRaisesRegex(RuntimeError, expected):
                    verify_dist_manifest(repository, manifest_path)

    def test_manifest_rejects_wheel_metadata_and_docs_content_mismatch(self) -> None:
        for case in ("metadata", "docs"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                repository = self.make_repository(Path(temp_dir))
                self.prepare_artifacts(repository)
                manifest_path = repository / "dist" / "manifest.json"
                create_dist_manifest(repository, "e" * 40, manifest_path)
                if case == "metadata":
                    self.mutate_manifest(
                        manifest_path,
                        lambda value: value["artifacts"][0]["metadata"].update(
                            version="9.9.9"
                        ),
                    )
                    expected = "wheel METADATA mismatch"
                else:
                    docs_zip = repository / "dist" / "panelsolver-docs-v2.3.4.zip"
                    docs_root = repository / "changed-docs"
                    docs_root.mkdir()
                    with zipfile.ZipFile(docs_zip) as archive:
                        archive.extractall(docs_root)
                    (docs_root / "index.html").write_text("changed", encoding="utf-8")
                    entries = [
                        (path.relative_to(docs_root).as_posix(), path)
                        for path in docs_root.rglob("*")
                        if path.is_file()
                    ]
                    entries.sort(key=lambda item: item[0])
                    write_deterministic_zip(docs_zip, entries)

                    def update_hash(value, archive_path=docs_zip):
                        value["artifacts"][2]["sha256"] = sha256_file(archive_path)

                    self.mutate_manifest(manifest_path, update_hash)
                    expected = "does not exactly match"
                with self.assertRaisesRegex(RuntimeError, expected):
                    verify_dist_manifest(repository, manifest_path)

    def test_lock_tag_changelog_and_prerelease_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_repository(Path(temp_dir))
            verify_lock_version(repository, "2.3.4")
            self.assertEqual("v2.3.4", expected_tag("2.3.4"))
            self.assertEqual("2.3.5.dev0", hypothetical_next_version("2.3.4"))
            verify_tag("v2.3.4", "2.3.4")
            self.assertEqual("- Released safely.\n", release_notes(repository, "2.3.4"))
            self.assertTrue(is_prerelease("0.1.0rc1"))
            self.assertFalse(is_prerelease("0.1.0"))
            with self.assertRaisesRegex(RuntimeError, "tag/version mismatch"):
                verify_tag("2.3.4", "2.3.4")

    def test_annotated_tag_matches_exact_main_and_wrong_forms_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            expected_commit = self.git(repository, "rev-parse", "HEAD")
            self.set_origin_main(repository, expected_commit)
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "release")
            self.assertEqual(
                expected_commit,
                verify_release_tag(repository, "v2.3.4", "refs/remotes/origin/main"),
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "v2.3.4")
            with self.assertRaisesRegex(RuntimeError, "must be annotated"):
                verify_release_tag(repository, "v2.3.4")
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "old")
            current = self.commit_file(repository, "candidate.txt", "new\n")
            self.set_origin_main(repository, current)
            with self.assertRaisesRegex(RuntimeError, "tag target mismatch"):
                verify_release_tag(repository, "v2.3.4", "refs/remotes/origin/main")

    def test_release_tag_rejects_wrong_version_lock_and_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.git(repository, "tag", "-a", "v2.3.5", "-m", "wrong")
            with self.assertRaisesRegex(RuntimeError, "tag/version mismatch"):
                verify_release_tag(repository, "v2.3.5")
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.commit_file(
                repository,
                "uv.lock",
                'version = 1\n\n[[package]]\nname = "panelsolver"\nversion = "2.3.5"\n',
            )
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "wrong lock")
            with self.assertRaisesRegex(RuntimeError, "uv.lock.*mismatch"):
                verify_release_tag(repository, "v2.3.4")
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = self.make_git_repository(Path(temp_dir))
            self.commit_file(repository, "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n")
            self.git(repository, "tag", "-a", "v2.3.4", "-m", "no notes")
            with self.assertRaisesRegex(RuntimeError, "no release section"):
                verify_release_tag(repository, "v2.3.4")

    def test_zero_open_tracker_gate_separates_issues_and_pull_requests(self) -> None:
        canonical = {"full_name": "pandorobo11/panelsolver"}
        with patch(
            "scripts.release_tools._github_api_json",
            side_effect=[canonical, {"total_count": 0}, {"total_count": 0}],
        ):
            verify_github_release_state()
        for counts in ((1, 0), (0, 1)):
            with self.subTest(counts=counts), patch(
                "scripts.release_tools._github_api_json",
                side_effect=[
                    canonical,
                    {"total_count": counts[0]},
                    {"total_count": counts[1]},
                ],
            ), self.assertRaisesRegex(RuntimeError, "zero open"):
                verify_github_release_state()
        with self.assertRaisesRegex(RuntimeError, "repository mismatch"):
            verify_github_release_state("pandorobo11/panel-solvers")

    def test_github_gate_requires_completely_successful_exact_main_push_ci(self) -> None:
        canonical = {"full_name": "pandorobo11/panelsolver"}
        green = {
            "workflow_runs": [
                {"name": "CI", "status": "completed", "conclusion": "success"}
            ]
        }
        with patch(
            "scripts.release_tools._github_api_json",
            side_effect=[
                canonical,
                {"total_count": 0},
                {"total_count": 0},
                green,
            ],
        ):
            verify_github_release_state(expected_commit="a" * 40)
        for runs in (
            {"workflow_runs": []},
            {
                "workflow_runs": [
                    {"name": "CI", "status": "in_progress", "conclusion": None}
                ]
            },
            {
                "workflow_runs": [
                    {"name": "CI", "status": "completed", "conclusion": "failure"}
                ]
            },
        ):
            with self.subTest(runs=runs), patch(
                "scripts.release_tools._github_api_json",
                side_effect=[
                    canonical,
                    {"total_count": 0},
                    {"total_count": 0},
                    runs,
                ],
            ), self.assertRaisesRegex(RuntimeError, "exact-main CI"):
                verify_github_release_state(expected_commit="b" * 40)

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
                    name.startswith(("PANELSOLVER_", "FMFSOLVER_", "NEWTSOLVER_"))
                    for name in environment
                )
            )


if __name__ == "__main__":
    unittest.main()
