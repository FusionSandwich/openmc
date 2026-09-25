"""Bind and compare C++ and Python provisional period bounding boxes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-receipt", type=Path, required=True)
    parser.add_argument("--compiled-output", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    previous = json.loads(args.python_receipt.read_text())
    if (previous.get("state") != "PROVISIONAL_PERIOD_PYTHON_BOUNDS_FINITE"
            or previous["sha256"]["candidate_h5"] != digest(args.h5)):
        raise ValueError("Python provisional period receipt mismatch")
    ids = previous["selected_member_ids"]
    command = [str(args.helper.resolve()), str(args.h5.resolve()),
               *map(str, ids)]
    process = subprocess.run(command, capture_output=True, timeout=30,
                             check=False)
    if (process.returncode != 0 or process.stderr
            or process.stdout != args.compiled_output.read_bytes()):
        raise ValueError("compiled bound output does not match current helper run")
    compiled = json.loads(process.stdout)
    if compiled["member_count"] != len(ids):
        raise ValueError("compiled member count mismatch")
    for cpp, python in (("lower_hex", "box_lower_cm"),
                        ("upper_hex", "box_upper_cm")):
        if len(compiled[cpp]) != 3 or len(previous[python]) != 3:
            raise ValueError("incomplete box")
        for exact_hex, value in zip(compiled[cpp], previous[python]):
            if float.fromhex(exact_hex) != value:
                raise ValueError(f"C++/Python period {cpp} mismatch")
    report = {
        "schema": "stellarcsg.period-swept-bound-parity/v1",
        "state": "PROVISIONAL_PERIOD_CPP_PYTHON_BOX_MATCH",
        "command": command,
        "exit_code": process.returncode,
        "selected_member_count": len(ids),
        "registered_whole_coil_span_count": previous["registered_whole_coil_span_count"],
        "manifest_admitted_span_count": previous["manifest_admitted_span_count"],
        "registered_unadmitted_span_count": previous["registered_unadmitted_span_count"],
        "matched_binary64_endpoints": 6,
        "sha256": {
            "auditor": digest(Path(__file__)),
            "python_receipt": digest(args.python_receipt),
            "compiled_output": digest(args.compiled_output),
            "helper": digest(args.helper),
            "helper_source": digest(args.helper_source),
            "standalone_library": digest(args.library),
            "candidate_h5": digest(args.h5),
        },
        "claim_boundary": "The current static C++ selected-set build and native OpenMC Python bounding-box path return identical binary64 bounds for 18 provisional whole coils. This is representation parity, not an approved physical one-period geometry: 1,452 registered whole-coil spans are outside the manifest's admitted span subset. No periodic-plane clipping/ownership, root completeness, source clearance, transport or latency is certified."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"], report["matched_binary64_endpoints"])


if __name__ == "__main__":
    main()
