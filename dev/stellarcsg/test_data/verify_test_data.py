#!/usr/bin/env python3
"""Verify the committed StellarCSG qualification-input manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(path: Path) -> int:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    checked = 0
    for record in manifest["files"]:
        copied = ROOT.parents[2] / record["copied_path"]
        if not copied.is_file():
            raise FileNotFoundError(copied)
        observed_size = copied.stat().st_size
        if observed_size != record["bytes"]:
            raise ValueError(
                f"size mismatch for {copied}: {observed_size} != {record['bytes']}"
            )
        observed_hash = sha256(copied)
        if observed_hash != record["sha256"]:
            raise ValueError(
                f"SHA-256 mismatch for {copied}: "
                f"{observed_hash} != {record['sha256']}"
            )
        checked += 1
    return checked


def main() -> int:
    manifests = sorted(ROOT.glob("*/MANIFEST.json"))
    if not manifests:
        raise FileNotFoundError("no test-data manifests")
    total = sum(verify_manifest(path) for path in manifests)
    print(f"verified {total} files from {len(manifests)} manifests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
