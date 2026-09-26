"""Sample an algebraic ellipse/tangent-plane route on analytic seam spans.

For each spline parameter, solve the ellipse-coordinate quadratic along the
fixed axial ray, then measure its tangent-plane residual. Sampling is only a
diagnostic for an eventual interval proof, not an exclusion certificate.
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


def bezier(controls: np.ndarray, span: int) -> np.ndarray:
    n = len(controls)
    a, b, c, d = [controls[k % n] for k in
                  (span - 1, span, span + 1, span + 2)]
    return np.stack(((a + 4.0 * b + c) / 6.0,
                     (2.0 * b + c) / 3.0,
                     (b + 2.0 * c) / 3.0,
                     (b + 4.0 * c + d) / 6.0))


def evaluate(control: np.ndarray, u: np.ndarray) -> np.ndarray:
    v = 1.0 - u
    weights = np.stack((v**3, 3.0 * u * v**2,
                        3.0 * u**2 * v, u**3), axis=1)
    return weights @ control


def derivative(control: np.ndarray, u: np.ndarray) -> np.ndarray:
    v = 1.0 - u
    weights = np.stack((v**2, 2.0 * u * v, u**2), axis=1)
    return weights @ (3.0 * np.diff(control, axis=0))


def summarize(group: h5py.Group, member: int, span: int,
              lead: float, samples: int) -> dict:
    u = np.linspace(0.0, 1.0, samples)
    center = evaluate(bezier(np.asarray(group["centerline_coefficients"]),
                             span), u)
    center_d = derivative(bezier(
        np.asarray(group["centerline_coefficients"]), span), u)
    tangent = center_d / np.linalg.norm(center_d, axis=1)[:, None]
    supplied = evaluate(bezier(np.asarray(group["normal_coefficients"]),
                               span), u)
    raw_normal = supplied - (supplied * tangent).sum(axis=1)[:, None] * tangent
    normal = raw_normal / np.linalg.norm(raw_normal, axis=1)[:, None]
    binormal = np.cross(tangent, normal)
    normal = np.cross(binormal, tangent)
    major = evaluate(bezier(np.asarray(group["major_radius_coefficients"]),
                            span), u)
    minor = evaluate(bezier(np.asarray(group["minor_radius_coefficients"]),
                            span), u)
    offset = np.column_stack((550.0 - center[:, 0],
                              -center[:, 1], -center[:, 2]))
    an = (offset * normal).sum(axis=1) / major
    ab = (offset * binormal).sum(axis=1) / minor
    bn = normal[:, 0] / major
    bb = binormal[:, 0] / minor
    qa = bn**2 + bb**2
    qb = -2.0 * (an * bn + ab * bb)
    qc = an**2 + ab**2 - 1.0
    discriminant = qb**2 - 4.0 * qa * qc
    finite = (qa > 0.0) & (discriminant >= 0.0)
    rows = []
    for sign in (-1.0, 1.0):
        with np.errstate(invalid="ignore", divide="ignore"):
            root = (-qb + sign * np.sqrt(np.maximum(discriminant, 0.0))) / (2.0 * qa)
        plane = ((550.0 - root - center[:, 0]) * tangent[:, 0]
                 - center[:, 1] * tangent[:, 1]
                 - center[:, 2] * tangent[:, 2])
        for gap in (1.0, 1.0e-5, 0.0, -4.0):
            mask = finite & np.isfinite(root) & (root >= 0.0) & (root <= lead - gap)
            count = int(mask.sum())
            if count:
                indices = np.flatnonzero(mask)
                index = int(indices[np.argmin(np.abs(plane[mask]))])
                witness = {"u": float(u[index]), "t_cm": float(root[index]),
                           "abs_plane_residual_cm": float(abs(plane[index]))}
            else:
                witness = None
            rows.append({"branch": int(sign), "gap_cm": gap,
                         "quadratic_roots_in_prefix": count,
                         "minimum_plane_residual": witness})
    return {"member": member, "span": span, "samples": samples,
            "tangent_x_range": [float(tangent[:, 0].min()),
                                float(tangent[:, 0].max())],
            "positive_quadratic_discriminants": int(finite.sum()),
            "branches": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=65537)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    if args.samples < 3:
        parser.error("samples must be at least three")
    rows = []
    with h5py.File(args.h5, "r") as handle:
        for member, lead in ((2, 16.0), (3, 17.000000000000227)):
            group = handle[f"/coils/coil_{member:03d}"]
            n = len(group["major_radius_coefficients"])
            for span in (0, n - 1):
                rows.append(summarize(group, member, span, lead, args.samples))
    report = {
        "schema": "stellarcsg.implicit-seam-sample/v1",
        "state": "SAMPLED_DIAGNOSTIC_NOT_INTERVAL_CERTIFIED",
        "h5_sha256": sha256(args.h5),
        "source_sha256": sha256(Path(__file__)),
        "ray_origin_cm": [550.0, 0.0, 0.0],
        "ray_direction": [-1.0, 0.0, 0.0],
        "rows": rows,
        "claim_boundary": "Finite spline samples and ordinary NumPy arithmetic; no interval exclusion, C++ path enclosure, or root uniqueness claim."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in rows:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
