"""Hash-bind native OpenMC initialization of the staged period-region XML."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    prior = json.loads((args.region / "receipt.json").read_text())
    if (prior["state"] != "PROVISIONAL_SECTOR_XML_ROUNDTRIP_ONLY"
            or prior["hashes"]["geometry_xml"] != sha256(args.region / "geometry.xml")):
        raise ValueError("period geometry XML differs from prior receipt")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.resolve().parent)
    env["OMP_NUM_THREADS"] = "1"
    loader = subprocess.run(["ldd", str(args.binary.resolve())],
                            capture_output=True, text=True, timeout=10,
                            check=False, env=env)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if (loader.returncode or len(bindings) != 1
            or str(args.library.resolve()) not in bindings[0]):
        raise ValueError("native helper is not bound to the selected OpenMC library")
    command = [str(args.binary.resolve()), str(args.region.resolve())]
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    result = subprocess.run(command, capture_output=True, text=True,
                            timeout=60, check=False, env=env)
    args.output.mkdir(parents=True)
    stdout = args.output / "stdout.jsonl"
    stderr = args.output / "stderr.txt"
    stdout.write_text(result.stdout)
    stderr.write_text(result.stderr)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    passed = (result.returncode == 0 and not result.stderr and len(rows) == 1
              and rows[0] == {
                  "state": "NATIVE_PERIOD_REGION_INITIALIZED",
                  "surfaces": 6, "cells": 2,
                  "rotational_periodic_pair": [901, 902],
                  "swept_selector_id": 903,
                  "transport_run": False})
    report = {
        "schema": "stellarcsg.native-period-region/v1",
        "state": "NATIVE_PERIOD_REGION_INITIALIZED_NO_TRANSPORT" if passed else "FAIL",
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": bindings[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {"auditor": sha256(Path(__file__)),
                   "helper_source": sha256(args.source),
                   "helper": sha256(args.binary),
                   "libopenmc": sha256(args.library),
                   "geometry_xml": sha256(args.region / "geometry.xml"),
                   "python_region_receipt": sha256(args.region / "receipt.json"),
                   "stdout": sha256(stdout), "stderr": sha256(stderr)},
        "claim_boundary": "Native OpenMC read_geometry_xml initialized the two unfilled sector cells, six surfaces, reciprocal rotational periodic pair and swept selector without transport. No particle crossed a periodic plane; the physical winding pack, general swept root completeness, source, materials and one-period simulation remain unqualified."
    }
    (args.output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"])
    if not passed:
        raise RuntimeError("native period-region initialization failed")


if __name__ == "__main__":
    main()
