"""Diagnose (ray distance, centerline parameter) root-tile conditioning.

This reconstructs spline powers from HDF5 using ordinary float arithmetic.
It does not enclose compiled C++ operations or certify any root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.optimize import root

from probe_swept_prefix_intervals import power_for_span


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equations(power: np.ndarray, distance: float, parameter: float) -> np.ndarray:
    value = ((power[:, 3] * parameter + power[:, 2]) * parameter
             + power[:, 1]) * parameter + power[:, 0]
    center_derivative = ((3 * power[:3, 3] * parameter
                          + 2 * power[:3, 2]) * parameter + power[:3, 1])
    tangent = center_derivative / np.linalg.norm(center_derivative)
    supplied = value[3:6]
    normal = supplied - np.dot(supplied, tangent) * tangent
    normal /= np.linalg.norm(normal)
    binormal = np.cross(tangent, normal)
    binormal /= np.linalg.norm(binormal)
    normal = np.cross(binormal, tangent)
    offset = np.array([550.0 - distance, 0.0, 0.0]) - value[:3]
    ellipse = ((np.dot(offset, normal) / value[6]) ** 2
               + (np.dot(offset, binormal) / value[7]) ** 2 - 1.0)
    stationarity = np.dot(offset, center_derivative)
    return np.array([ellipse, stationarity])


def jacobian(power: np.ndarray, distance: float, parameter: float) -> np.ndarray:
    # Finite differences are a conditioning diagnostic, not interval bounds.
    steps = np.array([1e-5, 1e-5])
    columns = []
    for index in range(2):
        delta = np.zeros(2)
        delta[index] = steps[index]
        plus = equations(power, distance + delta[0], parameter + delta[1])
        minus = equations(power, distance - delta[0], parameter - delta[1])
        columns.append((plus - minus) / (2 * steps[index]))
    return np.column_stack(columns)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    receipt = json.loads(args.native_receipt.read_text())
    if (receipt.get("state") != "BLOCKED_SINGLE_AND_COLLECTION_UNRESOLVED"
            or receipt.get("solver_probe_complete") is not True
            or sha256(args.h5) not in receipt.get("hashes", {}).values()):
        raise ValueError("native root diagnostic identity or status mismatch")
    results = []
    with h5py.File(args.h5) as handle:
        for probe in receipt["solver_probes"]:
            member = int(probe["member"])
            lead = float(probe["lead_distance_cm"])
            group = handle[f"coils/coil_{member:03d}"]
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            for span, initial_u in ((0, 0.0), (len(fields) - 1, 1.0)):
                power = power_for_span(fields, span)
                initial = equations(power, lead, initial_u)
                solved = root(lambda x: equations(power, x[0], x[1]),
                              [lead, initial_u], method="hybr", tol=1e-12)
                distance, parameter = map(float, solved.x)
                residual = equations(power, distance, parameter)
                matrix = jacobian(power, distance, parameter)
                results.append({
                    "member": member, "span": span,
                    "initial_distance_cm": lead, "initial_u": initial_u,
                    "initial_equations": initial.tolist(),
                    "root_solver_success": bool(solved.success),
                    "candidate_distance_cm": distance,
                    "candidate_u": parameter,
                    "candidate_in_stored_span": 0.0 <= parameter <= 1.0,
                    "candidate_equations": residual.tolist(),
                    "finite_difference_jacobian": matrix.tolist(),
                    "jacobian_determinant": float(np.linalg.det(matrix)),
                    "jacobian_condition_2": float(np.linalg.cond(matrix)),
                })
    report = {
        "schema": "stellarcsg.swept-root-tile-conditioning/v1",
        "state": "DIAGNOSTIC_NOT_ROOT_CERTIFIED",
        "source_sha256": sha256(Path(__file__)),
        "h5_sha256": sha256(args.h5),
        "native_receipt_sha256": sha256(args.native_receipt),
        "results": results,
        "claim_boundary": "Reconstructed float powers, SciPy root and finite-difference Jacobian do not certify existence, uniqueness, floating enclosures, or earliest-root ordering.",
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for row in results:
        print(json.dumps({key: row[key] for key in (
            "member", "span", "candidate_u", "jacobian_determinant",
            "jacobian_condition_2", "candidate_in_stored_span")}))


if __name__ == "__main__":
    main()
