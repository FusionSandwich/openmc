"""Bind two native 90-degree periodic-particle controls to their inputs."""

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
    parser.add_argument("--native-region-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    xml = args.region / "geometry.xml"
    prior = json.loads(args.native_region_receipt.read_text())
    if (prior["state"] != "NATIVE_PERIOD_REGION_INITIALIZED_NO_TRANSPORT"
            or prior["hashes"]["geometry_xml"] != sha256(xml)
            or prior["hashes"]["libopenmc"] != sha256(args.library)):
        raise ValueError("native geometry and library do not match the prior check")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.resolve().parent)
    env["OMP_NUM_THREADS"] = "1"
    binding = subprocess.run(["ldd", str(args.binary.resolve())],
                             capture_output=True, text=True, timeout=10,
                             check=False, env=env)
    lines = [line.strip() for line in binding.stdout.splitlines()
             if "libopenmc.so" in line]
    if (binding.returncode or len(lines) != 1
            or str(args.library.resolve()) not in lines[0]):
        raise ValueError("particle helper is bound to a different OpenMC library")
    command = [str(args.binary.resolve()), str(args.region.resolve())]
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    run = subprocess.run(command, capture_output=True, text=True, timeout=60,
                         check=False, env=env)
    args.output.mkdir(parents=True)
    stdout, stderr = args.output / "stdout.jsonl", args.output / "stderr.txt"
    stdout.write_text(run.stdout)
    stderr.write_text(run.stderr)
    rows = [json.loads(line) for line in run.stdout.splitlines()]
    passed = (run.returncode == 0 and not run.stderr and len(rows) == 1
              and rows[0] == {
                  "state": "NATIVE_PERIOD_PARTICLE_CROSSINGS_PASS",
                  "crossings": 2, "cell_id": 1002,
                  "transport_histories": 0})
    receipt = {
        "schema": "stellarcsg.native-period-particle/v1",
        "state": "NATIVE_PERIOD_PARTICLE_CONTROLS_PASS" if passed else "FAIL",
        "command": command,
        "exit_code": run.returncode,
        "loader_binding": lines[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {"auditor": sha256(Path(__file__)),
                   "helper_source": sha256(args.source),
                   "helper": sha256(args.binary),
                   "libopenmc": sha256(args.library),
                   "geometry_xml": sha256(xml),
                   "native_region_receipt": sha256(args.native_region_receipt),
                   "stdout": sha256(stdout), "stderr": sha256(stderr)},
        "claim_boundary": "Two deterministic native OpenMC particles cross the x=0 and y=0 rotational periodic planes in opposite directions at radius 2300 cm, beyond the selected coils' bounding box, and reenter the complement cell with expected phase space. This verifies the periodic BC control and model cell handoff only. No histories or swept-coil crossings, physical materials, source clearance or one-period transport are certified."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise RuntimeError("native periodic-particle controls did not pass")


if __name__ == "__main__":
    main()
