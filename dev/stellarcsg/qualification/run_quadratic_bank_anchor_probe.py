"""Hash-bound diagnostic for arbitrary-ray quadratic intervals on bank anchors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


BANK_SHA256 = "7348483e39128259a844d22a7618869a3f111604ea48d01e196a87fe0d396af7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "library", "bank", "source", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    for name in ("binary", "library", "bank", "source"):
        path = getattr(args, name)
        if not path.is_file():
            parser.error(f"input missing: {path}")
        setattr(args, name, path.resolve())
    if args.output.exists():
        parser.error("output must be new")
    if sha256(args.bank) != BANK_SHA256:
        parser.error("frozen bank hash changed")
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
    command = [str(args.binary), str(args.bank), "--quadratic-bank-anchors"]
    child = subprocess.run(command, text=True, capture_output=True,
                           timeout=40, check=False, env=env)
    (args.output / "stdout.jsonl").write_text(child.stdout)
    (args.output / "stderr.txt").write_text(child.stderr)
    try:
        rows = [json.loads(line) for line in child.stdout.splitlines()]
    except json.JSONDecodeError:
        rows = []
    cutoffs = {"a03": (0.00199, 0.002, 0.012),
               "a06": (0.0, 0.01),
               "a08": (1.99999, 2.0, 2.1),
               "a15": (1.99999, 2.0, 2.1)}
    expected = {(anchor, span, cutoff) for anchor, values in cutoffs.items()
                for span in (0, 63) for cutoff in values}
    actual = {(row.get("id"), row.get("span"), row.get("cutoff_cm"))
              for row in rows}
    valid = (child.returncode == 0 and len(rows) == len(expected)
             and actual == expected
             and all(row.get("kind") == "quadratic_bank_anchor"
                     and row.get("candidate_disposition")
                     in ("hit", "no_hit", "unresolved")
                     and isinstance(row.get("nodes"), int)
                     and isinstance(row.get("undecided"), int)
                     and len(row.get("outcomes", [])) == 6
                     for row in rows))
    receipt = {
        "schema": "stellarcsg.quadratic-bank-anchor-interval/v1",
        "state": ("EXPERIMENTAL_ARBITRARY_RAY_DIAGNOSTIC_ONLY" if valid
                  else "EXPERIMENT_INCOMPLETE"),
        "command": command,
        "exit_code": child.returncode,
        "loader_binding": matches[0],
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path): sha256(path) for path in
                   (args.binary, args.library, args.bank, args.source,
                    Path(__file__).resolve())},
        "compile_contract": "GCC 14.2 -O2 -fno-fast-math -ffp-contract=off",
        "outcome_order": ["excluded_value", "excluded_no_real_root",
                          "excluded_root_interval", "excluded_plane",
                          "undecided_frame", "undecided_root"],
        "rows": rows,
        "claim_boundary": "Diagnostic on four frozen torus anchors and two seam spans each. The ellipse equation, interval slacks, and compiled-power frame are not certified enclosures of the production acceptance path. No full-bank, transport, or performance qualification."
    }
    (args.output / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "rows": len(rows),
                      "excluded": sum(row["undecided"] == 0 for row in rows),
                      "undecided": sum(row["undecided"] != 0 for row in rows)}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
