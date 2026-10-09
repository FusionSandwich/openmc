"""Run local unit controls and write a compact machine-readable receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

import numpy
import scipy


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PACKET = REPO.parent / "stellarcsg-axis-integration-20261008" / "dev" / "stellarcsg" / "proposals" / "fourier_torus_20261009"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
start = time.perf_counter()
result = runner.run(suite)
test_seconds = time.perf_counter() - start
manifest_path = PACKET / "source_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
snapshot_verification = {
    row["snapshot"]: sha256(PACKET / row["snapshot"]) == row["sha256"]
    for row in manifest["files"]
}
snapshots_valid = len(snapshot_verification) == len(manifest["files"]) and all(snapshot_verification.values())
files = [HERE / "fourier_torus.py", HERE / "test_fourier_torus.py", HERE / "run_tests.py", HERE / "README.md"]
receipt = {
    "schema": "fourier-torus-prototype-receipt-v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS" if result.wasSuccessful() and snapshots_valid else "FAIL",
    "repository": str(REPO),
    "branch": git("branch", "--show-current"),
    "head": git("rev-parse", "HEAD"),
    "upstream_base": "origin/develop@9a62e431d3101799e6179a6d0cf3b37440062e23",
    "runtime": {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "executable": sys.executable,
    },
    "inputs": {
        "reviewer_packet_manifest": {
            "path": str(PACKET / "source_manifest.json"),
            "sha256": sha256(PACKET / "source_manifest.json"),
        },
        "wout_file": {"status": "NOT_USED", "reason": "synthetic coefficient controls only"},
    },
    "prototype_source_sha256": {path.name: sha256(path) for path in files},
    "verification": {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "functional_test_wall_seconds": test_seconds,
    },
    "costs": {
        "software_acquisition_bytes": 0,
        "native_build": "NOT_PERFORMED",
        "wout_load_seconds": None,
        "fit_construction_seconds": None,
        "peak_memory_bytes": None,
        "query_benchmark_seconds": None,
        "native_transport_seconds": None,
        "transport_speed_ratio": None,
    },
    "evidence_snapshot_hashes": snapshot_verification,
    "scope": "synthetic geometry controls; no certified Fourier-boundary ray query or transport claim",
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(f"receipt: {HERE / 'receipt.json'}")
sys.exit(0 if result.wasSuccessful() and snapshots_valid else 1)
