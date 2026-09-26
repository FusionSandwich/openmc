#!/usr/bin/env python3
"""Restore the verified periodic-axis milestone from its GitHub savepoint.

This helper exists because an earlier GitHub Actions materializer was corrupted.
It extracts the committed, hash-locked source snapshot into dev/stellarcsg while
preserving the handoff prompt and snapshot directory. Run only from a clean
checkout of the isolated feature branch.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_SHA256 = "5043bcd871b07067468ca9ba094e6da4b9fb2cc03f21f714248c71f1a9ecc44a"
ARCHIVE_RELATIVE = Path(
    "dev/stellarcsg/snapshots/periodic_axis_openmc_adapter_source.zip"
)
PREFIX = "stellarcsg_source_bundle/stellarcsg/"
PRESERVE = (
    Path("docs/LOCAL_CODEX_COMPLETION_PROMPT.md"),
    Path("docs/GITHUB_SAVEPOINT.md"),
    Path("snapshots"),
    Path("tools/restore_verified_milestone.py"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="OpenMC repository root (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Required to replace the existing dev/stellarcsg implementation",
    )
    args = parser.parse_args()

    root = args.repo_root.resolve()
    target = root / "dev/stellarcsg"
    archive = root / ARCHIVE_RELATIVE
    if not (root / ".git").exists():
        print(f"error: {root} is not a Git checkout", file=sys.stderr)
        return 2
    if not archive.is_file():
        print(f"error: missing savepoint archive: {archive}", file=sys.stderr)
        return 2
    observed = sha256(archive)
    if observed != EXPECTED_SHA256:
        print(
            f"error: archive SHA-256 mismatch: {observed} != {EXPECTED_SHA256}",
            file=sys.stderr,
        )
        return 2
    if not args.force:
        print("error: pass --force after confirming the checkout is clean", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="stellarcsg-restore-") as temp_name:
        temp = Path(temp_name)
        extracted = temp / "stellarcsg"
        extracted.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            members = [name for name in bundle.namelist() if name.startswith(PREFIX)]
            if not members:
                print("error: source prefix absent from savepoint archive", file=sys.stderr)
                return 2
            for name in members:
                relative_text = name[len(PREFIX) :]
                if not relative_text or relative_text.endswith("/"):
                    continue
                relative = Path(relative_text)
                if relative.is_absolute() or ".." in relative.parts:
                    print(f"error: unsafe archive member: {name}", file=sys.stderr)
                    return 2
                destination = extracted / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(name) as source, destination.open("wb") as sink:
                    shutil.copyfileobj(source, sink)

        preserved: dict[Path, Path] = {}
        preserve_root = temp / "preserved"
        for relative in PRESERVE:
            source = target / relative
            if not source.exists():
                continue
            destination = preserve_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            preserved[relative] = destination

        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(extracted, target)
        for relative, source in preserved.items():
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)

    print(f"restored verified StellarCSG milestone into {target}")
    print("next: run git diff --check, CMake/CTest, and Python tests before editing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
