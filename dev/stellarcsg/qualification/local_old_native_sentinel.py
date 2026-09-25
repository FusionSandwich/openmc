#!/usr/bin/env python3
"""Measure the recovered-old coil and native ZTorus as unlike-bank controls.

This is deliberately a sentinel receipt, not a matched geometry benchmark.
Native ZTorus uses its archived 64-ray repeated bank. The old coil executable
uses its own 1000 unique distance rays and only one untimed oracle ray.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from datetime import datetime, timezone


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], timeout: int) -> dict:
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=timeout, check=False)
    record = {"command": command, "exit_code": completed.returncode,
              "stdout": completed.stdout, "stderr": completed.stderr}
    try:
        record["result"] = json.loads(completed.stdout)
    except json.JSONDecodeError:
        record["result"] = None
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--coil", type=Path, required=True)
    parser.add_argument("--coil-dataset", default="/coils/coil_1031")
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--native-library", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=7)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error("at least three repetitions are required")
    for path in (args.old, args.coil, args.native, args.native_library):
        if not path.is_file():
            parser.error(f"missing input: {path}")
    if args.output.exists():
        parser.error("output must be new")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    loader = subprocess.run(["ldd", str(args.native.resolve())],
                            capture_output=True, text=True, check=False)
    bindings = [line for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if loader.returncode != 0 or len(bindings) != 1 or \
            str(args.native_library.resolve()) not in bindings[0]:
        parser.error("native executable is not bound to the specified OpenMC library")
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    receipt = {
        "schema": "stellarcsg.local-old-native-sentinel/v1",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "affinity": sorted(os.sched_getaffinity(0)),
        "source_commit": args.source_commit,
        "native_openmc_loader_binding": bindings[0].strip(),
        "inputs": {str(path.resolve()): digest(path) for path in
                   (args.old, args.coil, args.native, args.native_library)},
        "geometry_comparable": False,
        "bank_comparable": False,
        "interpretation": "Same-session absolute-cost sentinel ratio only. The old coil uses 1000 unique distance directions and one untimed oracle ray; native ZTorus repeats 64 rays 10000 times without an application result cache. Neither classification nor normal has a native matching control here. No candidate or transport is measured.",
        "attempts": [],
        "state": "INCOMPLETE",
    }
    commands = {
        "old_coil": [str(args.old.resolve()), str(args.coil.resolve()), args.coil_dataset, "1"],
        "native_ztorus": [str(args.native.resolve()), "--banks", "10000"],
    }
    for repetition in range(args.repetitions):
        order = ["native_ztorus", "old_coil"] if repetition % 2 else ["old_coil", "native_ztorus"]
        for lane in order:
            attempt = run(commands[lane], 120)
            attempt.update(lane=lane, repetition=repetition)
            receipt["attempts"].append(attempt)
            args.output.write_text(json.dumps(receipt, indent=2) + "\n")
            if attempt["exit_code"] != 0 or attempt["result"] is None:
                receipt["state"] = "FAIL"
                args.output.write_text(json.dumps(receipt, indent=2) + "\n")
                print(f"control failed: {lane} repetition {repetition}", file=sys.stderr)
                return 1
    old = [a["result"]["distance_ns_per_call"] for a in receipt["attempts"] if a["lane"] == "old_coil"]
    native = [a["result"]["ns_per_query"] for a in receipt["attempts"] if a["lane"] == "native_ztorus"]
    receipt["metrics"] = {
        "old_distance_ns_median_of_bank_means": statistics.median(old),
        "old_distance_ns_min_max": [min(old), max(old)],
        "native_distance_ns_median_of_bank_means": statistics.median(native),
        "native_distance_ns_min_max": [min(native), max(native)],
        "old_over_native_sentinel_cost_ratio": statistics.median(old) / statistics.median(native),
        "candidate_over_native_cost_ratio": None,
        "classification_cost_ratio": None,
        "normal_cost_ratio": None,
        "transport_throughput_ratio": None,
        "old_oracle_mismatches": [a["result"]["oracle_mismatches"] for a in receipt["attempts"] if a["lane"] == "old_coil"],
    }
    receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["state"] = "PASS"
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["metrics"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
