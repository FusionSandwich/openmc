"""Experimental centerline-hull exclusion for two analytic swept members.

The cubic B-spline centerline lies in the convex hull of its four Bezier
controls. A swept surface lies within the larger sphere of radius equal to the
largest nearby cross-section control. This probe subdivides those Bezier hulls
against an axial ray prefix. Its floating arithmetic is diagnostic, not a
production interval certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def bezier_controls(controls: np.ndarray, span: int) -> np.ndarray:
    n = len(controls)
    previous, first, second, following = [controls[k % n] for k in
                                           (span - 1, span, span + 1, span + 2)]
    return np.stack(((previous + 4 * first + second) / 6,
                     (2 * first + second) / 3,
                     (first + 2 * second) / 3,
                     (first + 4 * second + following) / 6))


def split_half(control: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    first = (control[:-1] + control[1:]) / 2
    second = (first[:-1] + first[1:]) / 2
    third = (second[0] + second[1]) / 2
    return (np.stack((control[0], first[0], second[0], third)),
            np.stack((third, second[1], first[2], control[3])))


def box_segment_distance(control: np.ndarray, low_x: float) -> float:
    lower = control.min(axis=0)
    upper = control.max(axis=0)
    distance = np.maximum(np.maximum(lower - [550.0, 0.0, 0.0],
                                     [low_x, 0.0, 0.0] - upper), 0.0)
    return float(np.linalg.norm(distance))


def excludes_tangent_plane(control: np.ndarray, low_x: float,
                           pad_cm2: float) -> bool:
    """Bound (ray point - center) dot the centerline derivative on a tile."""
    center_low = control.min(axis=0)
    center_high = control.max(axis=0)
    derivative = 3.0 * np.diff(control, axis=0)
    derivative_low = derivative.min(axis=0)
    derivative_high = derivative.max(axis=0)
    offset_low = np.array([low_x, 0.0, 0.0]) - center_high
    offset_high = np.array([550.0, 0.0, 0.0]) - center_low
    products = np.stack((offset_low * derivative_low,
                         offset_low * derivative_high,
                         offset_high * derivative_low,
                         offset_high * derivative_high))
    return (float(products.min(axis=0).sum()) > pad_cm2 or
            float(products.max(axis=0).sum()) < -pad_cm2)


def excludes_axial_support(control: np.ndarray, radius: float,
                           low_x: float, pad: float) -> bool:
    """Bound the x support of a radius-r tube normal to the tangent."""
    derivative = 3.0 * np.diff(control, axis=0)
    lower = derivative.min(axis=0)
    upper = derivative.max(axis=0)
    min_abs_x = max(0.0, lower[0], -upper[0])
    max_abs_y = max(abs(lower[1]), abs(upper[1]))
    max_abs_z = max(abs(lower[2]), abs(upper[2]))
    transverse = float(np.hypot(max_abs_y, max_abs_z))
    speed_bound = float(np.hypot(min_abs_x, transverse))
    support = radius if speed_bound == 0.0 else radius * transverse / speed_bound
    return float(control[:, 0].max()) + support + pad < low_x


def exclude_span(control: np.ndarray, radius: float, low_x: float,
                 pad: float, use_tangent: bool,
                 use_support: bool) -> tuple[bool, int, int]:
    stack = [(control, 0)]
    visited = 0
    max_depth = 0
    while stack:
        tile, depth = stack.pop()
        visited += 1
        max_depth = max(max_depth, depth)
        if box_segment_distance(tile, low_x) > radius + pad:
            continue
        if use_support and excludes_axial_support(tile, radius, low_x, pad):
            continue
        if use_tangent and excludes_tangent_plane(tile, low_x, 1.0e-2):
            continue
        if depth >= 30 or visited >= 10000:
            return False, visited, max_depth
        left, right = split_half(tile)
        stack.extend(((left, depth + 1), (right, depth + 1)))
    return True, visited, max_depth


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sampled_ellipse_axial_support(group: h5py.Group, span: int) -> dict:
    """Sample the oriented ellipse's maximum x; diagnostic, not a bound."""
    center_coeff = np.asarray(group["centerline_coefficients"], dtype=float)
    normal_coeff = np.asarray(group["normal_coefficients"], dtype=float)
    major_coeff = np.asarray(group["major_radius_coefficients"], dtype=float)
    minor_coeff = np.asarray(group["minor_radius_coefficients"], dtype=float)
    center_control = bezier_controls(center_coeff, span)
    normal_control = bezier_controls(normal_coeff, span)
    major_control = bezier_controls(major_coeff, span)
    minor_control = bezier_controls(minor_coeff, span)
    u = np.linspace(0.0, 1.0, 4097)
    weight = np.stack(((1 - u) ** 3, 3 * u * (1 - u) ** 2,
                       3 * u**2 * (1 - u), u**3), axis=1)
    derivative_weight = np.stack(((1 - u) ** 2, 2 * u * (1 - u), u**2), axis=1)
    center = weight @ center_control
    derivative = derivative_weight @ (3 * np.diff(center_control, axis=0))
    tangent = derivative / np.linalg.norm(derivative, axis=1)[:, None]
    supplied = weight @ normal_control
    raw_normal = supplied - (supplied * tangent).sum(axis=1)[:, None] * tangent
    normal = raw_normal / np.linalg.norm(raw_normal, axis=1)[:, None]
    binormal = np.cross(tangent, normal)
    major = weight @ major_control
    minor = weight @ minor_control
    maximum_x = center[:, 0] + np.hypot(major * normal[:, 0],
                                        minor * binormal[:, 0])
    index = int(np.argmax(maximum_x))
    return {"span": span, "sample_count": len(u),
            "maximum_sampled_surface_x_cm": float(maximum_x[index]),
            "at_local_u": float(u[index])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    results = []
    sampled_support = []
    with h5py.File(args.h5, "r") as handle:
        for member, lead in ((2, 16.0), (3, 17.000000000000227)):
            group = handle[f"/coils/coil_{member:03d}"]
            center = np.asarray(group["centerline_coefficients"], dtype=float)
            major = np.asarray(group["major_radius_coefficients"], dtype=float)
            minor = np.asarray(group["minor_radius_coefficients"], dtype=float)
            for gap in (1.0, 1.0e-5, 0.0, -4.0):
                for method in ("sphere", "sphere_tangent", "sphere_support_tangent"):
                    unknown = []
                    total_visits = 0
                    deepest = 0
                    for span in range(len(center)):
                        radius = max(float(max(major[k % len(center)],
                                               minor[k % len(center)]))
                                     for k in (span - 1, span, span + 1, span + 2))
                        excluded, visits, depth = exclude_span(
                            bezier_controls(center, span), radius,
                            550.0 - (lead - gap), 1.0e-5,
                            use_tangent=(method != "sphere"),
                            use_support=(method == "sphere_support_tangent"))
                        total_visits += visits
                        deepest = max(deepest, depth)
                        if not excluded:
                            unknown.append(span)
                    results.append({"member": member, "gap_cm": gap,
                                    "method": method, "span_count": len(center),
                                    "excluded": len(center) - len(unknown),
                                    "unknown_spans": unknown,
                                    "tile_visits": total_visits,
                                    "max_depth": deepest})
            for span in ((0, len(center) - 1)):
                sampled_support.append({"member": member, **
                                        sampled_ellipse_axial_support(group, span)})
    report = {"schema": "stellarcsg.centerline-prefix-feasibility/v4",
              "state": "EXPERIMENTAL_NOT_ROOT_CERTIFIED",
              "h5_sha256": sha256(args.h5),
              "source_sha256": sha256(Path(__file__)),
              "fixture_ray_origin_cm": [550.0, 0.0, 0.0],
              "fixture_ray_direction": [-1.0, 0.0, 0.0],
              "rounding_pad_cm": 1.0e-5,
              "tangent_dot_pad_cm2": 1.0e-2,
              "sampled_seam_axial_support": sampled_support,
              "results": results,
              "claim_boundary": "Floating Bezier hull and radius bounds are diagnostic; no formal arithmetic or production root-tile certificate."}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for result in results:
        print(json.dumps(result))
    for result in sampled_support:
        print(json.dumps({"kind": "sampled_seam_axial_support", **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
