"""Compare supplied WISTELL-D binormals with the runtime reconstructed frame.

This is a sampled payload-fidelity diagnostic, not a geometry enclosure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cubic(controls: np.ndarray, index: int, u: float) -> tuple[np.ndarray, np.ndarray]:
    """Uniform periodic cubic value and derivative in local span coordinate."""
    count = len(controls)
    p0, p1, p2, p3 = (controls[(index + offset) % count]
                      for offset in (-1, 0, 1, 2))
    c0 = (p0 + 4.0 * p1 + p2) / 6.0
    c1 = (-p0 + p2) / 2.0
    c2 = (p0 - 2.0 * p1 + p2) / 2.0
    c3 = (-p0 + 3.0 * p1 - 3.0 * p2 + p3) / 6.0
    value = ((c3 * u + c2) * u + c1) * u + c0
    derivative = (3.0 * c3 * u + 2.0 * c2) * u + c1
    return value, derivative


def unit(value: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(value))
    if not np.isfinite(length) or length <= 0.0:
        raise ValueError("nonfinite or zero frame vector")
    return value / length


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    manifest = json.loads(args.manifest.read_text())
    h5_hash = sha256(args.h5)
    if manifest["input_hashes"]["h5_sha256"] != h5_hash:
        raise ValueError("manifest does not bind this HDF5 payload")
    members = manifest["members"]
    if len(members) != 48 or len({row["member"] for row in members}) != 48:
        raise ValueError("expected 48 unique manifest members")
    rows = []
    with h5py.File(args.h5, "r") as handle:
        for member in members:
            group = handle[member["dataset"]]
            center = np.asarray(group["centerline_coefficients"], dtype=float).reshape(-1, 3)
            supplied_normal = np.asarray(group["normal_coefficients"], dtype=float).reshape(-1, 3)
            supplied_binormal = np.asarray(group["binormal_coefficients"], dtype=float).reshape(-1, 3)
            minor = np.asarray(group["minor_radius_coefficients"], dtype=float).reshape(-1)
            count = len(center)
            if (count != member["span_count"] or len(supplied_normal) != count
                    or len(supplied_binormal) != count or len(minor) != count):
                raise ValueError("payload control dimensions differ from manifest")
            largest = {"hypothetical_raw_binormal_shift_cm": -1.0}
            max_misalignment = 0.0
            min_abs_dot = 1.0
            max_supplied_norm_error = 0.0
            max_tangent_component = 0.0
            max_normal_component = 0.0
            max_transverse_axis_difference = 0.0
            for span in range(count):
                for u in (0.0, 0.5):
                    _, derivative = cubic(center, span, u)
                    normal, _ = cubic(supplied_normal, span, u)
                    binormal, _ = cubic(supplied_binormal, span, u)
                    radius, _ = cubic(minor, span, u)
                    tangent = unit(derivative)
                    normal = unit(normal - np.dot(normal, tangent) * tangent)
                    reconstructed = unit(np.cross(tangent, normal))
                    supplied_length = float(np.linalg.norm(binormal))
                    supplied = unit(binormal)
                    tangent_component = float(np.dot(supplied, tangent))
                    normal_component = float(np.dot(supplied, normal))
                    transverse = supplied - tangent_component * tangent \
                        - normal_component * normal
                    transverse_axis = unit(transverse)
                    transverse_difference = float(min(
                        np.linalg.norm(reconstructed - transverse_axis),
                        np.linalg.norm(reconstructed + transverse_axis)))
                    dot = float(np.dot(reconstructed, supplied))
                    abs_dot = min(1.0, abs(dot))
                    misalignment = float(min(np.linalg.norm(reconstructed - supplied),
                                             np.linalg.norm(reconstructed + supplied)))
                    displacement = float(radius * misalignment)
                    max_misalignment = max(max_misalignment, misalignment)
                    min_abs_dot = min(min_abs_dot, abs_dot)
                    max_supplied_norm_error = max(max_supplied_norm_error,
                                                  abs(supplied_length - 1.0))
                    max_tangent_component = max(max_tangent_component,
                                                abs(tangent_component))
                    max_normal_component = max(max_normal_component,
                                               abs(normal_component))
                    max_transverse_axis_difference = max(
                        max_transverse_axis_difference, transverse_difference)
                    if displacement > largest["hypothetical_raw_binormal_shift_cm"]:
                        largest = {"span": span, "u": u,
                                   "hypothetical_raw_binormal_shift_cm": displacement,
                                   "signed_dot": dot, "minor_radius_cm": float(radius),
                                   "supplied_tangent_component": tangent_component,
                                   "supplied_normal_component": normal_component,
                                   "transverse_axis_difference": transverse_difference}
            rows.append({"member": member["member"],
                         "sector_candidate": member["sector_candidate"],
                         "sample_count": 2 * count,
                         "min_abs_axis_dot": min_abs_dot,
                         "max_sign_invariant_axis_difference": max_misalignment,
                         "max_supplied_binormal_norm_error": max_supplied_norm_error,
                         "max_supplied_tangent_component": max_tangent_component,
                         "max_supplied_normal_component": max_normal_component,
                         "max_transverse_axis_difference": max_transverse_axis_difference,
                         "largest": largest})
    if len(rows) != 48 or sum(row["sector_candidate"] for row in rows) != 18:
        raise ValueError("sector member counts changed")
    output = {
        "schema": "stellarcsg.wistell-binormal-payload-audit/v1",
        "state": "SAMPLED_FRAME_FIDELITY_DIAGNOSTIC_ONLY",
        "hashes": {"h5_sha256": h5_hash,
                   "manifest_sha256": sha256(args.manifest),
                   "auditor_sha256": sha256(Path(__file__))},
        "all_member_max_hypothetical_raw_binormal_shift_cm": max(
            row["largest"]["hypothetical_raw_binormal_shift_cm"] for row in rows),
        "sector_member_max_hypothetical_raw_binormal_shift_cm": max(
            row["largest"]["hypothetical_raw_binormal_shift_cm"] for row in rows
            if row["sector_candidate"]),
        "rows": rows,
        "claim_boundary": "Compares normalized supplied binormal splines with the tangent-cross-normal frame at span starts and midpoints. Both the Python source definition and C++ runtime intentionally reconstruct the binormal; the raw-vector shift is hypothetical and is not an observed discrepancy between those implementations. Axis sign is ignored because a full ellipse is invariant to binormal sign. This is not a continuous bound, surface-set Hausdorff distance, or physical winding-pack fidelity certificate."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in
                      ("state", "all_member_max_hypothetical_raw_binormal_shift_cm",
                       "sector_member_max_hypothetical_raw_binormal_shift_cm")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
