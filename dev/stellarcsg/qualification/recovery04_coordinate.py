"""Run frozen-bank replays in fresh processes and retain bounded provenance.

This coordinator intentionally does not compile, install, or alter either
candidate.  Supply already-built archive/latest executables.  Seven process
repetitions prevent a previous replay's query cache from improving a result.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(executable: Path, bank: Path, wistell: Path | None, dataset: str) -> dict:
    command = [str(executable), "--replay", str(bank)]
    if wistell:
        command += ["--wistell-h5", str(wistell), "--wistell-dataset", dataset]
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    records = []
    malformed = 0
    for line in completed.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    summaries = [x for x in records if x.get("kind") == "summary"]
    return {"command": command, "returncode": completed.returncode,
            "stderr": completed.stderr, "records": records,
            "malformed_stdout_lines": malformed,
            "summary": summaries[-1] if summaries else None}


def invoke_retained_corpus(executable: Path) -> dict:
    """Keep the later 384-ray adversarial corpus distinct from the frozen bank."""
    completed = subprocess.run([str(executable)], text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    return {"command": [str(executable)], "returncode": completed.returncode,
            "stderr": completed.stderr,
            "json_lines": sum(1 for line in completed.stdout.splitlines()
                              if line.startswith("{"))}


def cross_version(archive: dict, latest: dict) -> dict:
    """Compare dispositions only; performance remains per-candidate evidence."""
    def queries(run: dict) -> dict:
        return {record["id"]: record for record in run["records"]
                if record.get("kind") == "query"}
    older, newer = queries(archive), queries(latest)
    mismatches = []
    for query_id in sorted(set(older) & set(newer)):
        a, b = older[query_id], newer[query_id]
        if a.get("candidate_found") != b.get("candidate_found"):
            mismatches.append(query_id)
        elif a.get("candidate_found") and abs(a["candidate_distance"] - b["candidate_distance"]) > 3e-7 * max(1.0, abs(a["candidate_distance"])):
            mismatches.append(query_id)
    return {"matched_queries": len(set(older) & set(newer)), "mismatched_query_ids": mismatches}


def metamorphic(run: dict) -> dict:
    rows = {x.get("id"): x for x in run["records"] if x.get("kind") == "query"}
    def same_distance(left: str, right: str, scale: float = 1.0) -> bool | None:
        a, b = rows.get(left), rows.get(right)
        if not a or not b or not a.get("candidate_found") or not b.get("candidate_found"):
            return None
        return abs(a["candidate_distance"] - scale*b["candidate_distance"]) <= 3e-7 * max(1.0, abs(a["candidate_distance"]))
    return {"direction_scaling_a09_equals_2xa10": same_distance("a09", "a10", 2.0),
            "rigid_a01_equals_a11": same_distance("a01", "a11")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--latest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--wistell-h5", type=Path)
    parser.add_argument("--expected-wistell-sha256")
    parser.add_argument("--wistell-dataset", default="/coils/coil_031")
    parser.add_argument("--adversarial-archive", type=Path)
    parser.add_argument("--adversarial-latest", type=Path)
    args = parser.parse_args()
    if not args.bank.is_file(): parser.error("bank is required and must already be frozen")
    for executable in (args.archive, args.latest):
        if not executable.is_file(): parser.error(f"missing executable: {executable}")
    if args.wistell_h5 and not args.wistell_h5.is_file(): parser.error("missing WISTELL HDF5")
    if args.expected_wistell_sha256 and not args.wistell_h5:
        parser.error("--expected-wistell-sha256 requires --wistell-h5")
    if args.expected_wistell_sha256 and file_hash(args.wistell_h5) != args.expected_wistell_sha256.lower():
        parser.error("WISTELL fixture SHA-256 does not match the explicit verified value")
    if bool(args.adversarial_archive) != bool(args.adversarial_latest):
        parser.error("provide both retained adversarial executables or neither")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "recovery04-frozen-bank-v1", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "bank": str(args.bank), "bank_sha256": file_hash(args.bank), "repetitions": 7,
               "wistell_fixture": None if not args.wistell_h5 else {"path": str(args.wistell_h5),
                 "sha256": file_hash(args.wistell_h5), "dataset": args.wistell_dataset},
               "cache_policy": "one unique persisted bank per fresh subprocess; no warmup",
               "limitations": ["bounded sample, not a completeness proof", "reference disposition is reported separately from candidate", "unavailable counters and timings remain null, never zero"],
               "archive": [], "latest": []}
    for name, executable in (("archive", args.archive), ("latest", args.latest)):
        for repetition in range(7):
            item = invoke(executable, args.bank, args.wistell_h5, args.wistell_dataset)
            item["repetition"] = repetition
            item["metamorphic"] = metamorphic(item)
            receipt[name].append(item)
    receipt["cross_version"] = [cross_version(receipt["archive"][i], receipt["latest"][i]) for i in range(7)]
    if args.adversarial_archive:
        receipt["retained_384_corpus"] = {"separate_from_frozen_bank": True,
            "archive": [invoke_retained_corpus(args.adversarial_archive) for _ in range(7)],
            "latest": [invoke_retained_corpus(args.adversarial_latest) for _ in range(7)]}
    args.out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="ascii")
    failures = sum((x["summary"] or {}).get("candidate_failures", 0) for side in (receipt["archive"], receipt["latest"]) for x in side)
    blocked = sum((x["summary"] or {}).get("blocked", 0) for side in (receipt["archive"], receipt["latest"]) for x in side)
    print(json.dumps({"out": str(args.out), "candidate_failures": failures, "blocked": blocked}))
    return 1 if failures else 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
