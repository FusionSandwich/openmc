"""Run the opt-in compiled-power interval experiment with a bound receipt."""

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
    for option in ("binary", "library", "h5", "source", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    for path in (args.binary, args.library, args.h5, args.source):
        if not path.is_file():
            parser.error(f"input missing: {path}")
    if args.output.exists():
        parser.error("output must be new")
    args.binary = args.binary.resolve()
    args.library = args.library.resolve()
    args.h5 = args.h5.resolve()
    args.source = args.source.resolve()
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(args.library.parent)
    environment["OMP_NUM_THREADS"] = "1"
    binding = subprocess.run(["ldd", str(args.binary)], text=True,
                             capture_output=True, timeout=10, env=environment)
    matches = [line.strip() for line in binding.stdout.splitlines()
               if "libopenmc.so" in line]
    if (binding.returncode or len(matches) != 1
            or str(args.library) not in matches[0]):
        raise RuntimeError("experiment is not bound to the selected libopenmc.so")
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True)
    command = [str(args.binary), str(args.h5)]
    result = subprocess.run(command, text=True, capture_output=True,
                            timeout=30, env=environment, check=False)
    (args.output / "stdout.jsonl").write_text(result.stdout)
    (args.output / "stderr.txt").write_text(result.stderr)
    try:
        rows = [json.loads(line) for line in result.stdout.splitlines()]
    except json.JSONDecodeError:
        rows = []
    underflow = [row for row in rows if row.get("kind") == "underflow_control"]
    span_rows = [row for row in rows if row.get("kind") == "span"]
    summaries = [row for row in rows if row.get("kind") == "member_summary"]
    unique_spans = {(row.get("member"), row.get("span")) for row in span_rows}
    span_counts_match = (len(unique_spans) == len(span_rows)
                         and len(span_rows) == sum(
                             row.get("selected", 0) for row in summaries)
                         and all(sum(item.get("prefix_excluded") is True
                                     for item in span_rows
                                     if item.get("member") == row.get("member"))
                                 == row.get("prefix_excluded")
                                 and sum(item.get("zero_gap_undecided") is True
                                         for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("zero_gap_undecided")
                                 for row in summaries))
    valid = (result.returncode == 0
             and underflow == [{"kind": "underflow_control",
                                "state": "undecided_frame"}]
             and span_counts_match
             and [row.get("member") for row in summaries] == [2, 3]
             and all(row.get("selected", 0) > 0
                     and row.get("prefix_excluded") == row.get("selected")
                     and row.get("zero_gap_undecided", 0) > 0
                     and row.get("negative_control_undecided", 0) > 0
                     and row.get("terminal_unresolved") is True
                     for row in summaries))
    receipt = {
        "schema": "stellarcsg.cpp-prefix-interval-probe/v1",
        "state": "EXPERIMENTAL_PREFIX_EXCLUDED_NOT_ROOT_CERTIFIED" if valid
                 else "EXPERIMENT_INCOMPLETE",
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": matches[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.h5, args.source)},
        "compile_contract": "GCC 14.2 -O2 -fno-fast-math -ffp-contract=off",
        "underflow_control": underflow,
        "span_counts_match": span_counts_match,
        "summaries": summaries,
        "production_solver_modified": False,
        "native_transport_run": False,
        "claim_boundary": "Stored compiled powers tested, but no complete floating-path audit or finite root-tile uniqueness proof; no tracking admission.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2)
                                                + "\n")
    print(json.dumps({"state": receipt["state"], "summaries": summaries}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
