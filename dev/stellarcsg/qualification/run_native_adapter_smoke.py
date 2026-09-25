"""Run the opt-in native adapter smoke once with loader and input receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--analytic-h5", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.binary, args.library, args.analytic_h5, args.source):
        if not path.is_file():
            parser.error(f"required input missing: {path}")
    args.binary = args.binary.resolve()
    args.library = args.library.resolve()
    args.analytic_h5 = args.analytic_h5.resolve()
    args.source = args.source.resolve()
    if args.output.exists():
        parser.error("output must be new")
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(args.library.parent)
    environment["OMP_NUM_THREADS"] = "1"
    loader = subprocess.run(["ldd", str(args.binary)], text=True,
                            capture_output=True, timeout=10, check=False,
                            env=environment)
    binding = [line.strip() for line in loader.stdout.splitlines()
               if "libopenmc.so" in line]
    if loader.returncode or len(binding) != 1 or str(args.library.resolve()) not in binding[0]:
        raise RuntimeError("native smoke is not bound to the specified libopenmc.so")
    args.output.mkdir(parents=True)
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    command = [str(args.binary), str(args.analytic_h5)]
    result = subprocess.run(command, text=True, capture_output=True,
                            timeout=120, env=environment, check=False)
    (args.output / "stdout.jsonl").write_text(result.stdout)
    (args.output / "stderr.txt").write_text(result.stderr)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    single_pass = (len(rows) == 5 and
                   rows[0].get("kind") == "native_stellarcsg_adapter_single" and
                   0 < rows[0].get("distance_cm", 0) <= 25 and
                   rows[0].get("native_transport") is False)
    solver_probes = rows[1:3]
    solver_probe_complete = (
        [row.get("member") for row in solver_probes] == [2, 3]
        and all(row.get("kind") == "native_stellarcsg_solver_probe"
                for row in solver_probes))
    member_probes = rows[3:5]
    probe_complete = ([row.get("member") for row in member_probes] == [2, 3]
                      and all(row.get("kind") ==
                              "native_stellarcsg_member_probe"
                              for row in member_probes))
    blocked_collection = (result.returncode == 1 and
                          "collection: Swept-spline member has an unresolved"
                          in result.stderr)
    receipt = {
        "schema": "stellarcsg.native-adapter-smoke/v1",
        "state": ("BLOCKED_COLLECTION_UNRESOLVED" if single_pass and
                  solver_probe_complete and probe_complete and
                  blocked_collection else "FAIL"),
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": binding[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.analytic_h5, args.source)},
        "single_pass": single_pass,
        "solver_probes": solver_probes,
        "solver_probe_complete": solver_probe_complete,
        "member_probes": member_probes,
        "probe_complete": probe_complete,
        "collection_blocked": blocked_collection,
        "native_transport_run": False,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "single_pass": single_pass,
                      "collection_blocked": blocked_collection}))
    return 2 if receipt["state"] == "BLOCKED_COLLECTION_UNRESOLVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
