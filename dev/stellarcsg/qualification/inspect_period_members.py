"""Inventory 90-degree rotational copies in a compiled WISTELL-D coil file.

This is a control-point diagnostic, not a continuous-surface equivalence proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    with h5py.File(args.h5, "r") as handle:
        keys = sorted(handle["coils"])
        fields = {
            key: {name: np.asarray(handle["coils"][key][name], dtype=np.float64)
                  for name in ("centerline_coefficients", "normal_coefficients",
                               "binormal_coefficients", "major_radius_coefficients",
                               "minor_radius_coefficients")}
            for key in keys}
    data = {key: values["centerline_coefficients"] for key, values in fields.items()}
    if any(points.ndim != 2 or points.shape[1] != 3 for points in data.values()):
        raise ValueError("centerline controls must be Nx3")
    if len({points.shape[0] for points in data.values()}) != 1:
        raise ValueError("centerline control counts differ")

    rotate = np.array([[0.0, -1.0, 0.0],
                       [1.0, 0.0, 0.0],
                       [0.0, 0.0, 1.0]])
    centroids = {key: points.mean(axis=0) for key, points in data.items()}
    rows = []
    for key in keys:
        target_centroid = rotate @ centroids[key]
        matches = sorted(
            ((float(np.linalg.norm(centroids[other] - target_centroid)), other)
             for other in keys),
            key=lambda pair: pair,
        )
        best_centroid_distance, other = matches[0]
        target = data[key] @ rotate.T
        candidate = data[other]
        best = None
        for reverse in (False, True):
            ordered = candidate[::-1] if reverse else candidate
            for shift in range(len(ordered)):
                residual = target - np.roll(ordered, shift, axis=0)
                rms = float(np.sqrt(np.mean(np.sum(residual * residual, axis=1))))
                if best is None or rms < best["rms_cm"]:
                    best = {"reverse": reverse, "shift": shift,
                            "rms_cm": rms,
                            "maximum_cm": float(np.max(np.linalg.norm(residual, axis=1)))}
        def aligned(values: np.ndarray) -> np.ndarray:
            ordered = values[::-1] if best["reverse"] else values
            return np.roll(ordered, best["shift"], axis=0)

        frame_residuals = {}
        frame_pairs = {}
        for name in ("normal_coefficients", "binormal_coefficients"):
            lhs = fields[key][name] @ rotate.T
            rhs = aligned(fields[other][name])
            frame_residuals[name] = float(np.max(np.linalg.norm(lhs - rhs, axis=1)))
            frame_pairs[name] = (lhs, rhs)
        radius_residuals = {}
        for name in ("major_radius_coefficients", "minor_radius_coefficients"):
            radius_residuals[name] = float(np.max(np.abs(
                fields[key][name] - aligned(fields[other][name]))))
        def shape_tensor(side: int) -> np.ndarray:
            normal = frame_pairs["normal_coefficients"][side]
            binormal = frame_pairs["binormal_coefficients"][side]
            if side == 0:
                major = fields[key]["major_radius_coefficients"]
                minor = fields[key]["minor_radius_coefficients"]
            else:
                major = aligned(fields[other]["major_radius_coefficients"])
                minor = aligned(fields[other]["minor_radius_coefficients"])
            return (major[:, None, None] ** 2 *
                    normal[:, :, None] * normal[:, None, :] +
                    minor[:, None, None] ** 2 *
                    binormal[:, :, None] * binormal[:, None, :])
        tensor_difference = shape_tensor(0) - shape_tensor(1)
        tensor_maximum = float(np.max(np.linalg.norm(
            tensor_difference.reshape(len(target), 9), axis=1)))
        phi = np.rad2deg(np.unwrap(np.arctan2(data[key][:, 1], data[key][:, 0])))
        angular_extent = [float(phi.min()), float(phi.max())]
        rows.append({"member": key, "rotated_match": other,
                     "centroid_distance_cm": best_centroid_distance,
                     "centerline_alignment": best,
                     "frame_maximum_residuals": frame_residuals,
                     "radius_maximum_residuals_cm": radius_residuals,
                     "ellipse_tensor_maximum_frobenius_cm2": tensor_maximum,
                     "angular_extent_degrees_unwrapped": angular_extent,
                     "crosses_90_degree_seam": bool(
                         np.floor(phi.min() / 90) != np.floor(phi.max() / 90))})
    successor = {row["member"]: row["rotated_match"] for row in rows}
    cycles = []
    unseen = set(keys)
    while unseen:
        start = min(unseen)
        path = []
        current = start
        while current not in path and current in unseen:
            path.append(current)
            unseen.remove(current)
            current = successor[current]
        cycles.append({"members": path, "closes": current == start})
    report = {
        "schema": "stellarcsg.period-member-inventory/v1",
        "h5_sha256": hashlib.sha256(args.h5.read_bytes()).hexdigest(),
        "member_count": len(keys),
        "controls_per_member": next(iter(data.values())).shape[0],
        "rotation_degrees": 90,
        "rows": rows,
        "cycles": cycles,
        "claim_boundary": "Control-point comparison only; continuous span geometry, winding-pack fidelity, interface ownership and transport remain unqualified.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"members": len(keys), "cycles": len(cycles),
                      "cycle_lengths": [len(c["members"]) for c in cycles],
                      "seam_crossing_members": sum(
                          row["crosses_90_degree_seam"] for row in rows),
                      "maximum_ellipse_tensor_frobenius_cm2": max(
                          row["ellipse_tensor_maximum_frobenius_cm2"] for row in rows),
                      "maximum_alignment_cm": max(
                          row["centerline_alignment"]["maximum_cm"] for row in rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
