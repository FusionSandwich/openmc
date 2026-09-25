"""Run the opt-in native adapter smoke once with loader and input receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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
    single_distance = (rows[0].get("distance_cm") if rows else None)
    single_pass = (len(rows) == 5 and
                   rows[0].get("kind") == "native_stellarcsg_adapter_single" and
                   isinstance(single_distance, (int, float)) and
                   math.isfinite(single_distance) and
                   abs(single_distance - 25.0) <= 1.0e-6 and
                   rows[0].get("state") == "HIT" and
                   rows[0].get("native_transport") is False)
    single_unresolved = (
        len(rows) == 5 and
        rows[0].get("kind") == "native_stellarcsg_adapter_single" and
        rows[0].get("state") == "ERROR" and
        single_distance is None and
        "native single: StellarCSG surface 902 has an unresolved nearest-boundary query"
        in result.stderr)
    solver_probes = rows[1:3]
    solver_probe_complete = (
        [row.get("member") for row in solver_probes] == [2, 3]
        and all(row.get("kind") == "native_stellarcsg_solver_probe"
                and row.get("found") is True
                and row.get("terminal_unresolved") is True
                and all(isinstance(row.get(field), (int, float))
                        and math.isfinite(row[field])
                        for field in ("lead_implicit_residual",
                                      "reference_implicit_residual"))
                for row in solver_probes))
    member_probes = rows[3:5]
    probe_complete = ([row.get("member") for row in member_probes] == [2, 3]
                      and all(row.get("kind") ==
                              "native_stellarcsg_member_probe"
                              and row.get("state") == "ERROR"
                              for row in member_probes)
                      and all(
                          f"native member {member}: StellarCSG surface 904 has an unresolved nearest-boundary query"
                          in result.stderr for member in (2, 3)))
    blocked_collection = (result.returncode == 1 and
                          "collection: Swept-spline member has an unresolved"
                          in result.stderr)
    if solver_probe_complete and probe_complete and blocked_collection:
        if single_unresolved:
            state = "BLOCKED_SINGLE_AND_COLLECTION_UNRESOLVED"
        elif single_pass:
            state = "BLOCKED_COLLECTION_UNRESOLVED"
        else:
            state = "FAIL"
    else:
        state = "FAIL"
    if state == "BLOCKED_SINGLE_AND_COLLECTION_UNRESOLVED":
        claim_boundary = (
            "The circular and shaped members registered through native OpenMC, "
            "but their member queries and the collection reject uncertified "
            "nearest-boundary results. Shaped diagnostic leads are reported "
            "separately; no distance is admitted and no transport ran.")
    elif state == "BLOCKED_COLLECTION_UNRESOLVED":
        claim_boundary = (
            "The circular spline registered through native OpenMC and returned "
            "the analytic crossing within 1e-6 cm. Shaped diagnostic leads "
            "remain terminal unresolved, as do their member adapters and "
            "collection; no transport ran.")
    else:
        claim_boundary = (
            "Native smoke failed outside its recognized blocked outcomes. "
            "No member crossing or transport is claimed.")
    receipt = {
        "schema": "stellarcsg.native-adapter-smoke/v4",
        "state": state,
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": binding[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.analytic_h5, args.source,
                    Path(__file__).resolve())},
        "single_expected_cm": 25.0,
        "single_tolerance_cm": 1.0e-6,
        "single_distance_cm": single_distance,
        "single_pass": single_pass,
        "single_unresolved": single_unresolved,
        "solver_probes": solver_probes,
        "solver_probe_complete": solver_probe_complete,
        "default_implicit_residual_acceptance_limit": 1.0e-8,
        "member_probes": member_probes,
        "probe_complete": probe_complete,
        "collection_blocked": blocked_collection,
        "native_transport_run": False,
        "claim_boundary": claim_boundary,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "single_pass": single_pass,
                      "collection_blocked": blocked_collection}))
    return 2 if state.startswith("BLOCKED_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
