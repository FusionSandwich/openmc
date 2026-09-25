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
                         and all(isinstance(row.get("u_endpoint_above_one_ulp"),
                                            bool) for row in span_rows)
                         and all(isinstance(row.get("padded_excluded"), bool)
                                 and (not row["padded_excluded"]
                                      or row["gap_slack_excluded"][2][2])
                                 for row in span_rows)
                         and all(not row.get("rectangle_excluded")
                                 or row.get("prefix_excluded") is True
                                 for row in span_rows)
                         and all(len(row.get("slack_excluded", [])) == 3
                                 and (not row["slack_excluded"][i + 1]
                                      or row["slack_excluded"][i])
                                 for row in span_rows for i in range(2))
                         and all(len(row.get("gap_slack_excluded", [])) == 3
                                 and all(len(line) == 3 for line in
                                         row["gap_slack_excluded"])
                                 and all(not row["gap_slack_excluded"][g][s + 1]
                                         or row["gap_slack_excluded"][g][s]
                                         for g in range(3) for s in range(2))
                                 and all(not row["gap_slack_excluded"][g][s]
                                         or row["gap_slack_excluded"][g + 1][s]
                                         for g in range(2) for s in range(3))
                                 for row in span_rows)
                         and all(sum(item.get("prefix_excluded") is True
                                     for item in span_rows
                                     if item.get("member") == row.get("member"))
                                 == row.get("prefix_excluded")
                                 and sum(item.get("u_endpoint_above_one_ulp")
                                         is True for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("u_endpoint_above_one_ulp")
                                 and sum(item.get("padded_excluded") is True
                                         for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("padded_excluded")
                                 and all(sum(item.get(field) is True
                                             for item in span_rows
                                             if item.get("member") == row.get("member"))
                                         == row.get(field)
                                         for field in
                                         ("padded_zero_gap_undecided",
                                          "padded_negative_undecided"))
                                 and sum(item.get("zero_gap_undecided") is True
                                         for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("zero_gap_undecided")
                                 and sum(item.get("rectangle_excluded") is True
                                         for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("rectangle_excluded")
                                 and sum(item.get("negative_control_undecided")
                                         is True for item in span_rows
                                         if item.get("member") == row.get("member"))
                                 == row.get("negative_control_undecided")
                                 and len(row.get("slack_excluded", [])) == 3
                                 and all(sum(item["slack_excluded"][i]
                                             for item in span_rows
                                             if item.get("member") == row.get("member"))
                                         == row.get("slack_excluded", [])[i]
                                         for i in range(3))
                                 and len(row.get("gap_slack_excluded", [])) == 3
                                 and all(len(line) == 3 for line in
                                         row["gap_slack_excluded"])
                                 and all(sum(item["gap_slack_excluded"][g][s]
                                             for item in span_rows
                                             if item.get("member") == row.get("member"))
                                         == row["gap_slack_excluded"][g][s]
                                         for g in range(3) for s in range(3))
                                 for row in summaries))
    valid = (result.returncode == 0
             and underflow == [{"kind": "underflow_control",
                                "state": "undecided_frame"}]
             and span_counts_match
             and [row.get("member") for row in summaries] == [2, 3]
             and all(row.get("selected", 0) > 0
                     and row.get("prefix_excluded") == row.get("selected")
                     and row.get("padded_excluded") == row.get("selected")
                     and row.get("zero_gap_undecided", 0) > 0
                     and row.get("negative_control_undecided", 0) > 0
                     and row.get("padded_zero_gap_undecided", 0) > 0
                     and row.get("padded_negative_undecided", 0) > 0
                     and row.get("terminal_unresolved") is True
                     for row in summaries))
    receipt = {
        "schema": "stellarcsg.cpp-prefix-interval-probe/v7",
        "state": "EXPERIMENTAL_RESIDUAL_PADDED_PREFIX_NOT_ROOT_CERTIFIED" if valid
                 else "EXPERIMENT_INCOMPLETE",
        "command": command,
        "exit_code": result.returncode,
        "loader_binding": matches[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.h5, args.source,
                    Path(__file__).resolve())},
        "compile_contract": "GCC 14.2 -O2 -fno-fast-math -ffp-contract=off",
        "unit_circle_slack_sweep": [1e-10, 1e-8, 1e-6],
        "gap_slack_matrix": {"gaps_cm": [1e-11, 1e-8, 1e-5],
                             "slacks": [1e-12, 1e-8, 1e-6]},
        "padded_case": {"gap_cm": 1e-5, "unit_circle_slack": 1e-6,
                        "projection_slack_formula":
                        "2*projected_tolerance+256*DBL_EPSILON*characteristic_length"},
        "underflow_control": underflow,
        "span_counts_match": span_counts_match,
        "summaries": summaries,
        "production_solver_modified": False,
        "native_transport_run": False,
        "claim_boundary": "The padded equations are an experimental stress test of accepted residual and arithmetic error, not a proof that all production floating operations are enclosed. Libm and finite root-tile uniqueness remain unaudited; no tracking admission.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2)
                                                + "\n")
    print(json.dumps({"state": receipt["state"], "summaries": summaries}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
