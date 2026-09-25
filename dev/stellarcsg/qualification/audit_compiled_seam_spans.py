"""Compare actual compiled seam span powers to the analytic HDF5 model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import h5py
import numpy as np

from probe_swept_prefix_intervals import power_for_span


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--angle-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    angle_receipt = json.loads(args.angle_receipt.read_text())
    if (angle_receipt.get("state") != "NATIVE_ARITHMETIC_DIAGNOSTIC_ONLY"
            or angle_receipt.get("h5_sha256") != sha256(args.h5)
            or angle_receipt.get("production_source_sha256")
            != sha256(args.production_source)):
        raise ValueError("angle receipt identity mismatch")
    process = subprocess.run([str(args.executable), str(args.h5)],
                             capture_output=True, text=True, check=True,
                             timeout=30)
    if process.stderr.strip():
        raise ValueError("compiled span helper emitted stderr")
    rows = [json.loads(line) for line in process.stdout.splitlines()]
    if (len(rows) != 4 or {(row["member"], row["span"]) for row in rows}
            != {(2, 0), (2, 255), (3, 0), (3, 383)}):
        raise ValueError("unexpected compiled spans")
    checks = []
    with h5py.File(args.h5) as handle:
        for row in rows:
            member, span, count = (int(row["member"]), int(row["span"]),
                                   int(row["sample_count"]))
            group = handle[f"coils/coil_{member:03d}"]
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            if len(fields) != count or len(row["power_hex"]) != 8:
                raise ValueError("compiled control count/shape mismatch")
            expected = power_for_span(fields, span)
            mismatches = []
            for field in range(8):
                if len(row["power_hex"][field]) != 4:
                    raise ValueError("compiled power row shape mismatch")
                for degree in range(4):
                    native = float.fromhex(row["power_hex"][field][degree])
                    model = float(expected[field, degree])
                    if native.hex() != model.hex():
                        mismatches.append({"field": field, "degree": degree,
                                           "native_hex": native.hex(),
                                           "model_hex": model.hex()})
            angle_limit_match = None
            if span == count - 1:
                previous = [item for item in angle_receipt["helper_stdout"]
                            if item["member"] == member]
                if len(previous) != 1:
                    raise ValueError("missing angle receipt member")
                angle_limit_match = (row["angle_min_hex"]
                                     == previous[0]["angle_min_hex"]
                                     and row["angle_max_hex"]
                                     == previous[0]["angle_max_hex"])
            checks.append({"member": member, "span": span,
                           "sample_count": count,
                           "coefficients_compared": 32,
                           "power_mismatch_count": len(mismatches),
                           "power_mismatches": mismatches,
                           "last_span_angle_limits_match": angle_limit_match})
    all_match = all(item["power_mismatch_count"] == 0 and
                    item["last_span_angle_limits_match"] is not False
                    for item in checks)
    report = {"schema": "stellarcsg.compiled-seam-span-identity/v1",
              "state": ("COMPILED_SEAM_POWERS_MATCH_MODEL_BITWISE" if all_match
                        else "COMPILED_SEAM_MODEL_MISMATCH"),
              "source_sha256": sha256(Path(__file__)),
              "helper_source_sha256": sha256(args.helper_source),
              "helper_executable_sha256": sha256(args.executable),
              "static_library_sha256": sha256(args.library),
              "production_source_sha256": sha256(args.production_source),
              "h5_sha256": sha256(args.h5),
              "angle_receipt_sha256": sha256(args.angle_receipt),
              "compiled_spans": rows, "checks": checks,
              "claim_boundary": "Reads actual CompiledSweptSplineSurface spans from the existing static library. Bitwise power/angle identity does not enclose floating frame evaluation or root solving, prove the static library's build provenance, or admit a native crossing."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for check in checks:
        print(json.dumps(check))
    if not all_match:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
