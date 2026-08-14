#!/usr/bin/env python3
"""Version-independent distribution verification and release dry-runs."""

from __future__ import annotations

import argparse
import email.parser
import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

_CANONICAL_SEPARATOR = re.compile(r"[-_.]+")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_DIST_MANIFEST_NAME = "panel-solvers.dist-manifest"
_DIST_MANIFEST_VERSION = 2
_ARTIFACT_KINDS = ("wheel", "sdist", "docs_zip", "examples_zip")
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def canonical_distribution_name(value: str) -> str:
    return _CANONICAL_SEPARATOR.sub("-", value).lower()


def project_identity(repository: Path) -> tuple[str, str]:
    with (repository / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    return str(project["name"]), str(project["version"])


def wheel_identity(wheel: Path) -> tuple[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_files = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise RuntimeError(
                f"expected exactly one METADATA file in {wheel.name}, "
                f"found {len(metadata_files)}"
            )
        metadata = email.parser.BytesParser().parsebytes(
            archive.read(metadata_files[0])
        )
    return str(metadata["Name"] or ""), str(metadata["Version"] or "")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_built_wheel(repository: Path, dist_dir: Path | None = None) -> Path:
    directory = dist_dir or repository / "dist"
    wheels = sorted(directory.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one wheel in {directory}, found {len(wheels)}: "
            f"{[path.name for path in wheels]}"
        )
    wheel = wheels[0]
    expected_name, expected_version = project_identity(repository)
    actual_name, actual_version = wheel_identity(wheel)
    if canonical_distribution_name(actual_name) != canonical_distribution_name(
        expected_name
    ):
        raise RuntimeError(
            f"wheel name mismatch: metadata={actual_name!r}, "
            f"project={expected_name!r}"
        )
    if actual_version != expected_version:
        raise RuntimeError(
            f"wheel version mismatch: metadata={actual_version!r}, "
            f"project={expected_version!r}"
        )
    expected_filename = (
        f"{canonical_distribution_name(expected_name).replace('-', '_')}-"
        f"{expected_version}-py3-none-any.whl"
    )
    if wheel.name != expected_filename:
        raise RuntimeError(
            f"wheel filename mismatch: found={wheel.name!r}, "
            f"expected={expected_filename!r}"
        )
    return wheel


def select_built_sdist(repository: Path, dist_dir: Path | None = None) -> Path:
    directory = dist_dir or repository / "dist"
    sdists = sorted(directory.glob("*.tar.gz"))
    if len(sdists) != 1:
        raise RuntimeError(
            f"expected exactly one sdist in {directory}, found {len(sdists)}: "
            f"{[path.name for path in sdists]}"
        )
    sdist = sdists[0]
    expected_name, expected_version = project_identity(repository)
    expected_filename = (
        f"{canonical_distribution_name(expected_name).replace('-', '_')}-"
        f"{expected_version}.tar.gz"
    )
    if sdist.name != expected_filename:
        raise RuntimeError(
            f"sdist filename mismatch: found={sdist.name!r}, "
            f"expected={expected_filename!r}"
        )
    return sdist


def _release_archive_path(repository: Path, kind: str, directory: Path) -> Path:
    _name, version = project_identity(repository)
    names = {
        "docs_zip": f"panel-solvers-docs-v{version}.zip",
        "examples_zip": f"panel-solvers-examples-v{version}.zip",
    }
    try:
        return directory / names[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported release archive kind: {kind}") from exc


def _zip_entries(root: Path, *, prefix: str = "") -> list[tuple[str, Path]]:
    entries: list[tuple[str, Path]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"release archive input must not be a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if any(part in {".DS_Store", "outputs"} for part in Path(relative).parts):
            continue
        entries.append((f"{prefix}{relative}", path))
    return entries


def write_deterministic_zip(
    output: Path,
    entries: list[tuple[str, Path]],
) -> Path:
    """Write a platform-neutral ZIP with stable order, metadata, and bytes."""
    names = [name for name, _path in entries]
    if names != sorted(names) or len(names) != len(set(names)):
        raise RuntimeError("deterministic ZIP entries must be sorted and unique")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, path in entries:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise RuntimeError(f"unsafe ZIP member name: {name!r}")
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, path.read_bytes())
    return output


def create_release_archives(
    repository: Path,
    dist_dir: Path | None = None,
    docs_site_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Create deterministic offline-docs and runnable-examples release ZIPs."""
    directory = dist_dir or repository / "dist"
    examples = repository / "examples"
    required_examples = (
        examples / "README.md",
        examples / "fmfsolver" / "basic.csv",
        examples / "newtsolver" / "basic.csv",
        examples / "geometry" / "plate.stl",
    )
    missing = [str(path) for path in required_examples if not path.is_file()]
    if missing:
        raise RuntimeError(f"required example files are missing: {missing}")
    if docs_site_dir is None:
        with tempfile.TemporaryDirectory(prefix="panel-wheel-docs-") as temporary:
            docs_site = Path(temporary) / "site"
            _extract_wheel_documentation(
                select_built_wheel(repository, directory),
                docs_site,
            )
            docs_zip = write_deterministic_zip(
                _release_archive_path(repository, "docs_zip", directory),
                _zip_entries(docs_site),
            )
    else:
        docs_site = docs_site_dir
        if not (docs_site / "index.html").is_file():
            raise RuntimeError(f"documentation site index is missing: {docs_site}")
        docs_zip = write_deterministic_zip(
            _release_archive_path(repository, "docs_zip", directory),
            _zip_entries(docs_site),
        )
    examples_zip = write_deterministic_zip(
        _release_archive_path(repository, "examples_zip", directory),
        _zip_entries(examples, prefix="examples/"),
    )
    _verify_release_zip("docs_zip", docs_zip)
    _verify_release_zip("examples_zip", examples_zip)
    return docs_zip, examples_zip


def _extract_wheel_documentation(wheel: Path, destination: Path) -> None:
    prefix = "panelsolver/_docs_site/"
    with zipfile.ZipFile(wheel) as archive:
        members = sorted(
            name
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        )
        if not members:
            raise RuntimeError("wheel contains no bundled documentation site")
        for member in members:
            relative = PurePosixPath(member.removeprefix(prefix))
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"wheel documentation path is unsafe: {member}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    if not (destination / "index.html").is_file():
        raise RuntimeError("wheel documentation site has no index.html")


def _verify_release_zip(kind: str, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if names != sorted(names) or len(names) != len(set(names)):
            raise RuntimeError(f"{kind} members must be sorted and unique")
        if any(
            Path(name).is_absolute() or ".." in Path(name).parts
            for name in names
        ):
            raise RuntimeError(f"{kind} contains an unsafe member")
        if kind == "docs_zip":
            required = {"index.html"}
        elif kind == "examples_zip":
            required = {
                "examples/README.md",
                "examples/fmfsolver/basic.csv",
                "examples/newtsolver/basic.csv",
                "examples/geometry/plate.stl",
            }
            if any("outputs" in Path(name).parts for name in names):
                raise RuntimeError("examples_zip contains generated outputs")
        else:
            raise ValueError(f"unsupported release archive kind: {kind}")
        missing = required - set(names)
        if missing:
            raise RuntimeError(f"{kind} is missing required members: {sorted(missing)}")


def _verify_docs_zip_matches_wheel(wheel: Path, docs_zip: Path) -> None:
    prefix = "panelsolver/_docs_site/"
    with zipfile.ZipFile(wheel) as wheel_archive, zipfile.ZipFile(
        docs_zip
    ) as docs_archive:
        wheel_members = {
            name.removeprefix(prefix): wheel_archive.read(name)
            for name in wheel_archive.namelist()
            if name.startswith(prefix) and not name.endswith("/")
        }
        docs_members = {
            name: docs_archive.read(name)
            for name in docs_archive.namelist()
            if not name.endswith("/")
        }
    if wheel_members != docs_members:
        raise RuntimeError("docs_zip content does not exactly match wheel documentation")


def _validated_commit_sha(value: str) -> str:
    normalized = value.strip().lower()
    if _COMMIT_SHA.fullmatch(normalized) is None:
        raise RuntimeError(f"expected a full 40-character commit SHA, found {value!r}")
    return normalized


def create_dist_manifest(
    repository: Path,
    commit_sha: str,
    output: Path,
    dist_dir: Path | None = None,
) -> dict[str, object]:
    directory = dist_dir or repository / "dist"
    wheel = select_built_wheel(repository, directory)
    sdist = select_built_sdist(repository, directory)
    docs_zip = _release_archive_path(repository, "docs_zip", directory)
    examples_zip = _release_archive_path(repository, "examples_zip", directory)
    _verify_release_zip("docs_zip", docs_zip)
    _verify_release_zip("examples_zip", examples_zip)
    metadata_name, metadata_version = wheel_identity(wheel)
    manifest: dict[str, object] = {
        "schema": {
            "name": _DIST_MANIFEST_NAME,
            "version": _DIST_MANIFEST_VERSION,
        },
        "github_commit_sha": _validated_commit_sha(commit_sha),
        "artifacts": [
            {
                "kind": "wheel",
                "filename": wheel.name,
                "sha256": sha256_file(wheel),
                "metadata": {
                    "name": metadata_name,
                    "version": metadata_version,
                },
            },
            {
                "kind": "sdist",
                "filename": sdist.name,
                "sha256": sha256_file(sdist),
            },
            {
                "kind": "docs_zip",
                "filename": docs_zip.name,
                "sha256": sha256_file(docs_zip),
            },
            {
                "kind": "examples_zip",
                "filename": examples_zip.name,
                "sha256": sha256_file(examples_zip),
            },
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return verify_dist_manifest(repository, output, directory, commit_sha)


def _manifest_artifact(
    value: object,
    *,
    field: str,
    directory: Path,
    expected_kind: str,
) -> tuple[Path, str, dict[str, object]]:
    if not isinstance(value, dict):
        raise TypeError(f"manifest {field} must be an object")
    allowed_keys = {"kind", "filename", "sha256"}
    if expected_kind == "wheel":
        allowed_keys.add("metadata")
    if set(value) != allowed_keys:
        raise RuntimeError(
            f"manifest {field} fields are invalid: {sorted(value)}"
        )
    if value.get("kind") != expected_kind:
        raise RuntimeError(
            f"manifest {field} kind mismatch: {value.get('kind')!r}"
        )
    filename = value.get("filename")
    expected_hash = value.get("sha256")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise RuntimeError(f"manifest {field} filename is invalid: {filename!r}")
    if not isinstance(expected_hash, str) or re.fullmatch(
        r"[0-9a-f]{64}", expected_hash
    ) is None:
        raise RuntimeError(f"manifest {field} SHA-256 is invalid")
    artifact = directory / filename
    if not artifact.is_file():
        raise RuntimeError(f"manifest {field} file is missing: {artifact}")
    actual_hash = sha256_file(artifact)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"manifest {field} hash mismatch: expected {expected_hash}, "
            f"found {actual_hash}"
        )
    return artifact, expected_hash, value


def verify_dist_manifest(
    repository: Path,
    manifest_path: Path,
    dist_dir: Path | None = None,
    expected_commit: str | None = None,
) -> dict[str, object]:
    directory = dist_dir or repository / "dist"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"could not read distribution manifest: {error}") from error
    if not isinstance(manifest, dict):
        raise TypeError("distribution manifest must be a JSON object")
    if set(manifest) != {"schema", "github_commit_sha", "artifacts"}:
        raise RuntimeError("distribution manifest has unexpected or missing fields")
    schema = manifest.get("schema")
    if schema != {
        "name": _DIST_MANIFEST_NAME,
        "version": _DIST_MANIFEST_VERSION,
    }:
        raise RuntimeError(f"unsupported distribution manifest schema: {schema!r}")
    commit_sha = manifest.get("github_commit_sha")
    if not isinstance(commit_sha, str):
        raise TypeError("manifest github_commit_sha must be a string")
    commit_sha = _validated_commit_sha(commit_sha)
    if expected_commit is not None:
        expected = _validated_commit_sha(expected_commit)
        if commit_sha != expected:
            raise RuntimeError(
                "manifest commit mismatch: "
                f"manifest={commit_sha}, checkout={expected}"
            )

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise TypeError("manifest artifacts must be an array")
    if len(artifacts) != len(_ARTIFACT_KINDS):
        raise RuntimeError(
            f"manifest must contain exactly {len(_ARTIFACT_KINDS)} artifacts"
        )
    kinds = [
        item.get("kind") if isinstance(item, dict) else None
        for item in artifacts
    ]
    if kinds != list(_ARTIFACT_KINDS):
        raise RuntimeError(
            f"manifest artifact kinds/order mismatch: found={kinds}, "
            f"expected={list(_ARTIFACT_KINDS)}"
        )
    entries: dict[str, tuple[Path, str, dict[str, object]]] = {}
    for kind, value in zip(_ARTIFACT_KINDS, artifacts, strict=True):
        entries[kind] = _manifest_artifact(
            value,
            field=kind,
            directory=directory,
            expected_kind=kind,
        )
    filenames = [entry[0].name for entry in entries.values()]
    if len(filenames) != len(set(filenames)):
        raise RuntimeError("manifest artifact filenames must be unique")

    wheel = entries["wheel"][0]
    sdist = entries["sdist"][0]
    selected_wheel = select_built_wheel(repository, directory)
    selected_sdist = select_built_sdist(repository, directory)
    if wheel != selected_wheel or sdist != selected_sdist:
        raise RuntimeError("manifest does not identify the selected distributions")

    for kind in ("docs_zip", "examples_zip"):
        artifact = entries[kind][0]
        if artifact != _release_archive_path(repository, kind, directory):
            raise RuntimeError(f"manifest {kind} filename does not match project version")
        _verify_release_zip(kind, artifact)
    _verify_docs_zip_matches_wheel(wheel, entries["docs_zip"][0])

    expected_files = set(filenames)
    if manifest_path.resolve().parent == directory.resolve():
        expected_files.add(manifest_path.name)
    # uv may place this VCS sentinel in an output directory; it is not uploaded
    # by Actions and is not a release artifact.
    actual_files = {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name != ".gitignore"
    }
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        extra = sorted(actual_files - expected_files)
        raise RuntimeError(
            f"distribution artifact set mismatch: missing={missing}, extra={extra}"
        )

    wheel_entry = entries["wheel"][2]
    metadata = wheel_entry.get("metadata")
    if not isinstance(metadata, dict):
        raise TypeError("manifest wheel metadata must be an object")
    actual_name, actual_version = wheel_identity(wheel)
    expected_name, expected_version = project_identity(repository)
    if metadata.get("name") != actual_name or metadata.get("version") != actual_version:
        raise RuntimeError(
            "manifest wheel METADATA mismatch: "
            f"manifest={metadata!r}, wheel={{'name': {actual_name!r}, "
            f"'version': {actual_version!r}}}"
        )
    if canonical_distribution_name(actual_name) != canonical_distribution_name(
        expected_name
    ) or actual_version != expected_version:
        raise RuntimeError(
            "wheel METADATA project mismatch: "
            f"wheel={actual_name!r} {actual_version!r}, "
            f"project={expected_name!r} {expected_version!r}"
        )
    return manifest


def verify_lock_version(repository: Path, version: str) -> None:
    with (repository / "uv.lock").open("rb") as stream:
        packages = tomllib.load(stream)["package"]
    matches = [item for item in packages if item.get("name") == "panel-solvers"]
    if len(matches) != 1 or matches[0].get("version") != version:
        found = [item.get("version") for item in matches]
        raise RuntimeError(
            f"uv.lock panel-solvers version mismatch: expected {version}, found {found}"
        )


def expected_tag(version: str) -> str:
    return f"v{version}"


def hypothetical_next_version(version: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        raise RuntimeError(f"cannot derive a dry-run version from {version!r}")
    major, minor, patch = (int(item) for item in match.groups())
    return f"{major}.{minor}.{patch + 1}.dev0"


def verify_tag(tag: str, version: str) -> None:
    expected = expected_tag(version)
    if tag != expected:
        raise RuntimeError(f"tag/version mismatch: tag={tag}, expected={expected}")


def _git_output(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"git {' '.join(arguments)} failed in {repository}: {detail}"
        )
    return result.stdout.strip()


def verify_tag_target(
    repository: Path,
    tag: str,
    expected_commit: str | None = None,
) -> str:
    reference = f"refs/tags/{tag}"
    object_type = _git_output(repository, "cat-file", "-t", reference)
    if object_type != "tag":
        raise RuntimeError(
            f"release tag {tag!r} must be annotated; object type is {object_type!r}"
        )

    peeled_commit = _git_output(repository, "rev-parse", f"{reference}^{{}}")
    expected = expected_commit or "HEAD"
    resolved_expected = _git_output(
        repository,
        "rev-parse",
        "--verify",
        f"{expected}^{{commit}}",
    )
    if peeled_commit != resolved_expected:
        raise RuntimeError(
            "release tag target mismatch: "
            f"tag={peeled_commit}, expected={resolved_expected}"
        )
    return peeled_commit


def verify_release_tag(
    repository: Path,
    tag: str,
    expected_commit: str | None = None,
) -> str:
    name, version = project_identity(repository)
    if canonical_distribution_name(name) != "panel-solvers":
        raise RuntimeError(f"unexpected project name: {name}")
    verify_tag(tag, version)
    verify_lock_version(repository, version)
    release_notes(repository, version)
    return verify_tag_target(repository, tag, expected_commit)


def release_notes(repository: Path, version: str) -> str:
    changelog = (repository / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = re.compile(
        rf"^## \[{re.escape(version)}\](?: - .+)?$",
        re.MULTILINE,
    )
    match = heading.search(changelog)
    if match is None:
        raise RuntimeError(f"CHANGELOG.md has no release section for {version}")
    start = match.end()
    next_heading = re.search(r"^## ", changelog[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(changelog)
    notes = changelog[start:end].strip()
    if not notes:
        raise RuntimeError(f"CHANGELOG.md release section {version} is empty")
    return notes + "\n"


def reinstall_built_wheel(repository: Path, dist_dir: Path | None = None) -> Path:
    wheel = select_built_wheel(repository, dist_dir)
    subprocess.run(
        ["uv", "pip", "uninstall", "panel-solvers"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", str(wheel)],
        cwd=repository,
        check=True,
    )
    installed = importlib.metadata.version("panel-solvers")
    expected = project_identity(repository)[1]
    if installed != expected:
        raise RuntimeError(
            f"installed distribution version mismatch: {installed} != {expected}"
        )
    return wheel


def verify_wheel_contents(repository: Path, wheel: Path) -> None:
    """Verify offline docs are packaged and MkDocs is not a runtime dependency."""
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required = {
            "panelsolver/_docs_site/index.html",
            "panelsolver/_docs_site/solvers/fmfsolver.html",
            "panelsolver/_docs_site/solvers/newtsolver.html",
        }
        missing = required - names
        if missing:
            raise RuntimeError(
                f"wheel is missing packaged documentation: {sorted(missing)}"
            )
        metadata_files = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise RuntimeError("wheel must contain exactly one METADATA file")
        metadata = email.parser.BytesParser().parsebytes(
            archive.read(metadata_files[0])
        )
        runtime_requirements = metadata.get_all("Requires-Dist", [])
        if any(
            re.match(r"^\s*mkdocs\b", requirement, re.IGNORECASE) is not None
            for requirement in runtime_requirements
        ):
            raise RuntimeError("MkDocs must not be a wheel runtime dependency")
        expected_name, expected_version = project_identity(repository)
        if (
            canonical_distribution_name(str(metadata["Name"] or ""))
            != canonical_distribution_name(expected_name)
            or str(metadata["Version"] or "") != expected_version
        ):
            raise RuntimeError("wheel METADATA does not match project identity")


def verify_sdist_contents(repository: Path, sdist: Path) -> None:
    """Verify source inputs needed to rebuild the documentation-bearing wheel."""
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
    roots = {name.split("/", 1)[0] for name in names if name}
    if len(roots) != 1:
        raise RuntimeError(f"sdist must have one archive root, found {sorted(roots)}")
    root = next(iter(roots))
    required = {
        f"{root}/pyproject.toml",
        f"{root}/mkdocs.yml",
        f"{root}/hatch_build.py",
        f"{root}/docs/index.md",
        f"{root}/src/panelsolver/docs_site.py",
        f"{root}/examples/README.md",
    }
    missing = required - set(names)
    if missing:
        raise RuntimeError(f"sdist is missing required source files: {sorted(missing)}")


def verify_built_distributions(
    repository: Path,
    dist_dir: Path | None = None,
) -> None:
    """Inspect wheel/sdist and rebuild a documentation-bearing wheel from sdist."""
    directory = dist_dir or repository / "dist"
    wheel = select_built_wheel(repository, directory)
    sdist = select_built_sdist(repository, directory)
    verify_wheel_contents(repository, wheel)
    verify_sdist_contents(repository, sdist)
    with tempfile.TemporaryDirectory(prefix="panel-sdist-rebuild-") as temporary:
        rebuilt_dir = Path(temporary) / "dist"
        subprocess.run(
            [
                "uv",
                "build",
                "--wheel",
                "--out-dir",
                str(rebuilt_dir),
                str(sdist.resolve()),
            ],
            cwd=Path(temporary),
            check=True,
        )
        rebuilt_wheel = select_built_wheel(repository, rebuilt_dir)
        verify_wheel_contents(repository, rebuilt_wheel)


def _replace_version(repository: Path, old: str, new: str) -> None:
    pyproject = repository / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    old_line = f'version = "{old}"'
    new_line = f'version = "{new}"'
    if text.count(old_line) != 1:
        raise RuntimeError("project.version was not uniquely replaceable")
    pyproject.write_text(text.replace(old_line, new_line), encoding="utf-8")

    lock = repository / "uv.lock"
    text = lock.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(\[\[package\]\]\nname = "panel-solvers"\nversion = ")[^"]+("\n)'
    )
    text, replacements = pattern.subn(rf"\g<1>{new}\g<2>", text)
    if replacements != 1:
        raise RuntimeError("uv.lock project version was not uniquely replaceable")
    lock.write_text(text, encoding="utf-8")

    changelog = repository / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    marker = "## [Unreleased]\n"
    dry_run_notes = (
        f"{marker}\n## [{new}] - DRY RUN\n\n"
        "- Verify version-independent build, install, notes, and tag checks.\n"
    )
    if text.count(marker) != 1:
        raise RuntimeError("CHANGELOG.md Unreleased section was not uniquely found")
    changelog.write_text(text.replace(marker, dry_run_notes), encoding="utf-8")


def _venv_python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def dry_run(repository: Path, version: str | None = None) -> None:
    current_name, current_version = project_identity(repository)
    version = version or hypothetical_next_version(current_version)
    if version == current_version:
        raise RuntimeError("dry-run version must differ from project.version")
    if canonical_distribution_name(current_name) != "panel-solvers":
        raise RuntimeError(f"unexpected project name: {current_name}")

    with tempfile.TemporaryDirectory(prefix="panel_release_dry_run_") as temp_dir:
        root = Path(temp_dir)
        checkout = root / "checkout"
        shutil.copytree(
            repository,
            checkout,
            ignore=shutil.ignore_patterns(
                ".git",
                ".hatch-build",
                ".venv",
                ".reference",
                "__pycache__",
                "dist",
                "outputs",
                "site",
            ),
        )
        _replace_version(checkout, current_version, version)
        verify_lock_version(checkout, version)
        verify_tag(expected_tag(version), version)
        release_notes(checkout, version)

        dist_dir = root / "dist"
        subprocess.run(
            ["uv", "build", "--out-dir", str(dist_dir)],
            cwd=checkout,
            check=True,
        )
        wheel = select_built_wheel(checkout, dist_dir)
        sdist = select_built_sdist(checkout, dist_dir)
        verify_wheel_contents(checkout, wheel)
        verify_sdist_contents(checkout, sdist)

        venv = root / "venv"
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(venv)],
            check=True,
        )
        python = _venv_python(venv)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "--no-deps", str(wheel)],
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-c",
                (
                    "import importlib.metadata as m; "
                    f"assert m.version('panel-solvers') == {version!r}"
                ),
            ],
            cwd=root,
            check=True,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("verify-wheel", "reinstall-wheel"):
        selected = subparsers.add_parser(command)
        selected.add_argument("repository", type=Path)
        selected.add_argument("--dist-dir", type=Path)
    create_manifest = subparsers.add_parser("create-manifest")
    create_manifest.add_argument("repository", type=Path)
    create_manifest.add_argument("--commit-sha", required=True)
    create_manifest.add_argument("--output", required=True, type=Path)
    create_manifest.add_argument("--dist-dir", type=Path)
    verify_manifest = subparsers.add_parser("verify-manifest")
    verify_manifest.add_argument("repository", type=Path)
    verify_manifest.add_argument("--manifest", required=True, type=Path)
    verify_manifest.add_argument("--dist-dir", type=Path)
    verify_manifest.add_argument("--expected-commit")
    archives = subparsers.add_parser("create-release-archives")
    archives.add_argument("repository", type=Path)
    archives.add_argument("--dist-dir", type=Path)
    archives.add_argument("--docs-site-dir", type=Path)
    distributions = subparsers.add_parser("verify-distributions")
    distributions.add_argument("repository", type=Path)
    distributions.add_argument("--dist-dir", type=Path)
    tag = subparsers.add_parser("verify-tag")
    tag.add_argument("repository", type=Path)
    tag.add_argument("tag")
    tag.add_argument("--expected-commit")
    notes = subparsers.add_parser("release-notes")
    notes.add_argument("repository", type=Path)
    notes.add_argument("--output", required=True, type=Path)
    probe = subparsers.add_parser("dry-run")
    probe.add_argument("repository", type=Path)
    probe.add_argument("--version")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = args.repository.resolve()
    if args.command == "verify-wheel":
        print(select_built_wheel(repository, args.dist_dir))
    elif args.command == "reinstall-wheel":
        print(reinstall_built_wheel(repository, args.dist_dir))
    elif args.command == "create-manifest":
        manifest = create_dist_manifest(
            repository,
            args.commit_sha,
            args.output,
            args.dist_dir,
        )
        print(json.dumps(manifest, sort_keys=True))
    elif args.command == "verify-manifest":
        manifest = verify_dist_manifest(
            repository,
            args.manifest,
            args.dist_dir,
            args.expected_commit,
        )
        print(json.dumps(manifest, sort_keys=True))
    elif args.command == "create-release-archives":
        print(
            "\n".join(
                str(path)
                for path in create_release_archives(
                    repository,
                    args.dist_dir,
                    args.docs_site_dir,
                )
            )
        )
    elif args.command == "verify-distributions":
        verify_built_distributions(repository, args.dist_dir)
    elif args.command == "verify-tag":
        print(verify_release_tag(repository, args.tag, args.expected_commit))
    elif args.command == "release-notes":
        _name, version = project_identity(repository)
        args.output.write_text(release_notes(repository, version), encoding="utf-8")
    else:
        dry_run(repository, args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
