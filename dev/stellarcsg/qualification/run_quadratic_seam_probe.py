"""Run and verify the compiled-power algebraic seam-prefix experiment."""

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
    for name in ("binary", "library", "h5", "source", "sample", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    for name in ("binary", "library", "h5", "source", "sample"):
        path = getattr(args, name)
        if not path.is_file():
            parser.error(f"input missing: {path}")
        setattr(args, name, path.resolve())
    if args.output.exists():
        parser.error("output must be new")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.parent)
    env["OMP_NUM_THREADS"] = "1"
    ldd = subprocess.run(["ldd", str(args.binary)], text=True,
                         capture_output=True, timeout=10, env=env)
    matches = [line.strip() for line in ldd.stdout.splitlines()
               if "libopenmc.so" in line]
    if (ldd.returncode or len(matches) != 1
            or str(args.library) not in matches[0]):
        raise RuntimeError("experiment is not bound to the selected libopenmc.so")
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True)
    command = [str(args.binary), str(args.h5), "--quadratic-seams"]
    child = subprocess.run(command, text=True, capture_output=True,
                           timeout=20, check=False, env=env)
    (args.output / "stdout.jsonl").write_text(child.stdout)
    (args.output / "stderr.txt").write_text(child.stderr)
    try:
        rows = [json.loads(line) for line in child.stdout.splitlines()]
    except json.JSONDecodeError:
        rows = []
    keys = {(row.get("member"), row.get("span"), row.get("gap_cm"))
            for row in rows}
    expected = {(member, span, gap)
                for member, last in ((2, 255), (3, 383))
                for span in (0, last)
                for gap in (1.0, 1.0e-5, 0.0, -4.0)}
    valid = (child.returncode == 0 and len(rows) == 16
             and keys == expected
             and all(row.get("kind") == "quadratic_seam"
                     and row.get("slack") == 1.0e-6
                     and row.get("plane_slack_cm") == 1.0e-4
                     and isinstance(row.get("nodes"), int)
                     and isinstance(row.get("undecided"), int)
                     and len(row.get("outcomes", [])) == 6
                     for row in rows)
             and all(row["undecided"] == 0 and row["nodes"] == 1
                     and row["outcomes"][0] == 1
                     for row in rows if row["gap_cm"] == 1.0)
             and all(row["undecided"] > 0
                     for row in rows if row["gap_cm"] <= 0.0))
    narrow_excluded = sum(row["gap_cm"] == 1.0e-5
                          and row["undecided"] == 0 for row in rows)
    receipt = {
        "schema": "stellarcsg.quadratic-seam-interval/v2",
        "state": ("EXPERIMENTAL_NARROW_PREFIX_NOT_ROOT_CERTIFIED"
                  if narrow_excluded == 4 else
                  "EXPERIMENTAL_ONE_CM_PREFIX_ONLY_NOT_ROOT_CERTIFIED")
                 if valid else "EXPERIMENT_INCOMPLETE",
        "command": command,
        "exit_code": child.returncode,
        "loader_binding": matches[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.h5, args.source,
                    args.sample, Path(__file__).resolve())},
        "compile_contract": "GCC 14.2 -O2 -fno-fast-math -ffp-contract=off",
        "outcome_order": ["excluded_value", "excluded_no_real_root",
                          "excluded_root_interval", "excluded_plane",
                          "undecided_frame", "undecided_root"],
        "narrow_prefix_excluded_count": narrow_excluded,
        "rows": rows,
        "claim_boundary": "Off-production interval model on compiled powers; its algebraic ellipse condition and stress slack are not an audited enclosure of the production parametric/libm path. The finite lead neighborhood, root uniqueness and other floating bounds remain unproved. No transport or performance qualification."
    }
    (args.output / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "rows": len(rows),
                      "one_cm_excluded": sum(row["gap_cm"] == 1.0
                                             and row["undecided"] == 0
                                             for row in rows),
                      "narrow_excluded": narrow_excluded}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
