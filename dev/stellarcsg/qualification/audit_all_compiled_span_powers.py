"""Bitwise-audit every analytic shaped span against the compiled instance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import h5py
import numpy as np

from probe_swept_prefix_intervals import power_for_span


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def same_bits(a: float, b: float) -> bool:
    return struct.pack("!d", a) == struct.pack("!d", b)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--reconstruction-source", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--seam-identity", type=Path, required=True)
    parser.add_argument("--global-model", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()
    if args.raw_output.exists() or args.receipt_output.exists():
        parser.error("both outputs must be new")
    seam = json.loads(args.seam_identity.read_text())
    global_model = json.loads(args.global_model.read_text())
    h5_hash = sha256(args.h5)
    if (seam.get("state") != "COMPILED_SEAM_POWERS_MATCH_MODEL_BITWISE"
            or seam.get("h5_sha256") != h5_hash
            or seam.get("static_library_sha256") != sha256(args.library)
            or global_model.get("state")
            != "REAL_MODEL_GLOBAL_NEAREST_LAST_SPAN"
            or global_model.get("h5_sha256") != h5_hash):
        raise ValueError("prior identity or static-library binding mismatch")
    process = subprocess.run([str(args.executable), str(args.h5)],
                             capture_output=True, text=True, check=True,
                             timeout=60)
    if process.stderr.strip():
        raise ValueError("compiled helper emitted stderr")
    rows = [json.loads(line) for line in process.stdout.splitlines()]
    seen = set()
    mismatches = []
    mismatch_count = 0
    coefficients = angle_limits = 0
    member_counts = {}
    with h5py.File(args.h5) as handle:
        for member in (2, 3):
            group = handle[f"coils/coil_{member:03d}"]
            member_counts[member] = len(group["centerline_coefficients"])
        if len(rows) != sum(member_counts.values()):
            raise ValueError("missing compiled span rows")
        fields_by_member = {}
        for member in (2, 3):
            group = handle[f"coils/coil_{member:03d}"]
            fields_by_member[member] = np.column_stack((
                group["centerline_coefficients"][:],
                group["normal_coefficients"][:],
                group["major_radius_coefficients"][:],
                group["minor_radius_coefficients"][:]))
        for row in rows:
            member, span, count = (int(row["member"]), int(row["span"]),
                                   int(row["sample_count"]))
            if (member not in member_counts or count != member_counts[member]
                    or not 0 <= span < count or (member, span) in seen):
                raise ValueError("duplicate or wrong compiled member/span")
            seen.add((member, span))
            if len(row["power_hex"]) != 8 or any(
                    len(power) != 4 for power in row["power_hex"]):
                raise ValueError("compiled power shape mismatch")
            expected = power_for_span(fields_by_member[member], span)
            for field in range(8):
                for degree in range(4):
                    native = float.fromhex(row["power_hex"][field][degree])
                    model = float(expected[field, degree])
                    coefficients += 1
                    if not same_bits(native, model):
                        mismatch_count += 1
                        if len(mismatches) < 32:
                            mismatches.append({"member": member, "span": span,
                                               "field": field, "degree": degree,
                                               "native_hex": native.hex(),
                                               "model_hex": model.hex()})
            two_pi = 2.0 * 3.141592653589793238462643383279502884
            step = two_pi / float(count)
            angle_min = step * float(span)
            angle_max = angle_min + step
            for name, expected_angle in (("angle_min", angle_min),
                                         ("angle_max", angle_max)):
                native = float.fromhex(row[f"{name}_hex"])
                angle_limits += 1
                if not same_bits(native, expected_angle):
                    mismatch_count += 1
                    if len(mismatches) < 32:
                        mismatches.append({"member": member, "span": span,
                                           "field": name,
                                           "native_hex": native.hex(),
                                           "model_hex": expected_angle.hex()})
    if seen != {(member, span) for member, count in member_counts.items()
                for span in range(count)}:
        raise ValueError("compiled span coverage is incomplete")
    raw_bytes = process.stdout.encode("utf-8")
    args.raw_output.write_bytes(raw_bytes)
    receipt = {"schema": "stellarcsg.all-compiled-span-identity/v1",
               "state": ("ALL_ANALYTIC_SHAPED_SPANS_BITWISE_IDENTICAL"
                         if mismatch_count == 0 else "COMPILED_SPAN_MISMATCH"),
               "source_sha256": sha256(Path(__file__)),
               "helper_source_sha256": sha256(args.helper_source),
               "helper_executable_sha256": sha256(args.executable),
               "static_library_sha256": sha256(args.library),
               "production_source_sha256": sha256(args.production_source),
               "reconstruction_source_sha256": sha256(args.reconstruction_source),
               "h5_sha256": h5_hash,
               "seam_identity_sha256": sha256(args.seam_identity),
               "global_model_sha256": sha256(args.global_model),
               "raw_output_basename": args.raw_output.name,
               "raw_output_sha256": hashlib.sha256(raw_bytes).hexdigest(),
               "span_count": len(rows),
               "member_span_counts": {str(key): value
                                      for key, value in member_counts.items()},
               "coefficients_compared": coefficients,
               "angle_limits_compared": angle_limits,
               "mismatch_count": mismatch_count,
               "mismatch_preview": mismatches,
               "claim_boundary": "All eight stored-power fields and both angle limits match bitwise between reconstructed HDF5 and the existing compiled standalone instances for analytic shaped members 2/3. This does not certify rounded frame/nearest-root/BVH behavior, generic import, physical WISTELL-D fidelity, or a native hit."}
    args.receipt_output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in (
        "state", "span_count", "coefficients_compared",
        "angle_limits_compared", "mismatch_count", "mismatch_preview")}))
    if mismatch_count:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
