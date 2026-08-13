#!/usr/bin/env python3
"""Version-independent distribution verification and release dry-runs."""

from __future__ import annotations

import argparse
import email.parser
import importlib.metadata
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

_CANONICAL_SEPARATOR = re.compile(r"[-_.]+")


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
    return wheel


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
                ".venv",
                ".reference",
                "__pycache__",
                "dist",
                "outputs",
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
        archives = sorted(dist_dir.glob("*.tar.gz"))
        if len(archives) != 1:
            raise RuntimeError(
                f"expected exactly one sdist, found {[path.name for path in archives]}"
            )

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
    tag = subparsers.add_parser("verify-tag")
    tag.add_argument("repository", type=Path)
    tag.add_argument("tag")
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
    elif args.command == "verify-tag":
        name, version = project_identity(repository)
        if canonical_distribution_name(name) != "panel-solvers":
            raise RuntimeError(f"unexpected project name: {name}")
        verify_lock_version(repository, version)
        verify_tag(args.tag, version)
        release_notes(repository, version)
    elif args.command == "release-notes":
        _name, version = project_identity(repository)
        args.output.write_text(release_notes(repository, version), encoding="utf-8")
    else:
        dry_run(repository, args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
