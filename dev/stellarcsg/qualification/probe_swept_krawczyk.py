"""Experimental interval-Jacobian check of paired swept-coil seam tiles.

Uses reconstructed HDF5 powers and a real-arithmetic ellipse/stationarity
model. Even a contracting tile here does not certify the compiled C++ path,
the globally nearest centerline, or one-period transport.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np

from probe_swept_prefix_intervals import I, power_for_span


ZERO = I.point(0.0)
ONE = I.point(1.0)
TWO = I.point(2.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive_sqrt(value: I) -> I:
    if value.hi < 0 or not math.isfinite(value.hi):
        return I(-math.inf, math.inf)
    lower = max(0.0, value.lo)
    return I(0.0 if lower == 0 else math.nextafter(math.sqrt(lower), -math.inf),
             math.nextafter(math.sqrt(value.hi), math.inf))


@dataclass(frozen=True)
class D:
    value: I
    dt: I = ZERO
    du: I = ZERO

    @staticmethod
    def constant(value: float) -> "D":
        return D(I.point(value))

    def __add__(self, other: "D") -> "D":
        return D(self.value + other.value, self.dt + other.dt, self.du + other.du)

    def __neg__(self) -> "D":
        return D(-self.value, -self.dt, -self.du)

    def __sub__(self, other: "D") -> "D":
        return self + -other

    def __mul__(self, other: "D") -> "D":
        return D(self.value * other.value,
                 self.dt * other.value + self.value * other.dt,
                 self.du * other.value + self.value * other.du)

    def square(self) -> "D":
        return D(self.value.square(), TWO * self.value * self.dt,
                 TWO * self.value * self.du)

    def reciprocal(self) -> "D":
        inverse = ONE / self.value
        denominator = self.value.square()
        return D(inverse, -self.dt / denominator, -self.du / denominator)

    def __truediv__(self, other: "D") -> "D":
        return self * other.reciprocal()

    def sqrt(self) -> "D":
        value = positive_sqrt(self.value)
        denominator = TWO * value
        return D(value, self.dt / denominator, self.du / denominator)


def dot(a: list[D], b: list[D]) -> D:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: list[D], b: list[D]) -> list[D]:
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def normalized(a: list[D]) -> list[D]:
    magnitude = (a[0].square() + a[1].square() + a[2].square()).sqrt()
    return [value / magnitude for value in a]


def polynomial(power: np.ndarray, field: int, u: D) -> D:
    p = power[field]
    return ((D.constant(float(p[3])) * u + D.constant(float(p[2]))) * u
            + D.constant(float(p[1]))) * u + D.constant(float(p[0]))


def equations(power: np.ndarray, t: I, u: I) -> list[D]:
    parameter = D(u, ZERO, ONE)
    distance = D(t, ONE, ZERO)
    center = [polynomial(power, field, parameter) for field in range(3)]
    derivative = [((D.constant(3 * float(power[field, 3])) * parameter
                    + D.constant(2 * float(power[field, 2]))) * parameter
                   + D.constant(float(power[field, 1]))) for field in range(3)]
    tangent = normalized(derivative)
    supplied = [polynomial(power, field, parameter) for field in range(3, 6)]
    projection = dot(supplied, tangent)
    normal = normalized([supplied[i] - projection * tangent[i]
                         for i in range(3)])
    binormal = normalized(cross(tangent, normal))
    normal = cross(binormal, tangent)
    offset = [D.constant(550.0) - distance - center[0],
              -center[1], -center[2]]
    major = polynomial(power, 6, parameter)
    minor = polynomial(power, 7, parameter)
    ellipse = (dot(offset, normal) / major).square() + (
        dot(offset, binormal) / minor).square() - D.constant(1.0)
    stationarity = dot(offset, derivative)
    return [ellipse, stationarity]


def finite_interval(value: I) -> bool:
    return math.isfinite(value.lo) and math.isfinite(value.hi) and value.lo <= value.hi


def as_pair(value: I) -> list[float]:
    return [value.lo, value.hi]


def classify(power: np.ndarray, t0: float, u0: float,
             t_width: float, u_width: float, span: int,
             count: int) -> dict:
    t_box = I(t0 - t_width, t0 + t_width)
    u_box = I(max(0.0, u0 - u_width), min(1.0, u0 + u_width))
    x0_t = min(max(t0, t_box.lo), t_box.hi)
    x0_u = min(max(u0, u_box.lo), u_box.hi)
    box = [t_box, u_box]
    x0 = [x0_t, x0_u]
    at_point = equations(power, I.point(x0_t), I.point(x0_u))
    on_box = equations(power, t_box, u_box)
    value = [item.value for item in at_point]
    jacobian = [[item.dt, item.du] for item in on_box]
    finite = all(finite_interval(item) for item in value) and all(
        finite_interval(item) for row in jacobian for item in row)
    output = {"span": span, "sample_count": count,
              "center": x0, "t_width_cm": t_width, "u_width": u_width,
              "box": [as_pair(item) for item in box],
              "point_residual": [as_pair(item) for item in value],
              "jacobian_interval": [[as_pair(item) for item in row]
                                    for row in jacobian],
              "finite_interval_model": finite}
    if not finite:
        output["state"] = "UNDECIDED_NONFINITE"
        return output
    midpoint_jacobian = np.array([[(entry.lo + entry.hi) / 2
                                    for entry in row] for row in jacobian])
    try:
        inverse = np.linalg.inv(midpoint_jacobian)
    except np.linalg.LinAlgError:
        output["state"] = "UNDECIDED_SINGULAR_MIDPOINT"
        return output
    base = []
    matrix = []
    krawczyk = []
    for i in range(2):
        base_i = I.point(x0[i])
        row = []
        for j in range(2):
            base_i = base_i - I.point(float(inverse[i, j])) * value[j]
        for j in range(2):
            entry = I.point(float(i == j))
            for k in range(2):
                entry = entry - I.point(float(inverse[i, k])) * jacobian[k][j]
            row.append(entry)
        k_i = base_i
        for j in range(2):
            k_i = k_i + row[j] * (box[j] - I.point(x0[j]))
        base.append(base_i)
        matrix.append(row)
        krawczyk.append(k_i)
    row_norm = max(sum(max(abs(entry.lo), abs(entry.hi)) for entry in row)
                   for row in matrix)
    strict_inside = all(k.lo > b.lo and k.hi < b.hi
                        for k, b in zip(krawczyk, box))
    disjoint = any(k.hi < b.lo or k.lo > b.hi
                   for k, b in zip(krawczyk, box))
    output.update({"krawczyk": [as_pair(item) for item in krawczyk],
                   "contraction_norm_inf": row_norm,
                   "strict_inside": strict_inside,
                   "disjoint": disjoint,
                   "state": ("MODEL_UNIQUE_EXISTENCE_CANDIDATE" if strict_inside
                             and row_norm < 1 else "MODEL_EXCLUSION_CANDIDATE"
                             if disjoint else "UNDECIDED")})
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--conditioning", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    previous = json.loads(args.conditioning.read_text())
    if (previous.get("state") != "DIAGNOSTIC_NOT_ROOT_CERTIFIED"
            or previous.get("h5_sha256") != sha256(args.h5)):
        raise ValueError("conditioning and HDF5 identities disagree")
    results = []
    with h5py.File(args.h5) as handle:
        for earlier in previous["results"]:
            member = int(earlier["member"])
            span = int(earlier["span"])
            group = handle[f"coils/coil_{member:03d}"]
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            power = power_for_span(fields, span)
            for t_width, u_width in ((1e-5, 1e-6), (1e-6, 1e-7),
                                     (1e-7, 1e-8), (1e-8, 1e-9)):
                row = classify(power, float(earlier["candidate_distance_cm"]),
                               float(earlier["candidate_u"]), t_width,
                               u_width, span, len(fields))
                row["member"] = member
                results.append(row)
    report = {"schema": "stellarcsg.swept-krawczyk-feasibility/v1",
              "state": "EXPERIMENTAL_RECONSTRUCTED_MODEL_ONLY",
              "source_sha256": sha256(Path(__file__)),
              "h5_sha256": sha256(args.h5),
              "conditioning_sha256": sha256(args.conditioning),
              "results": results,
              "claim_boundary": "Outward float intervals apply to reconstructed HDF5 powers and a real-arithmetic two-equation model only. No compiled C++ enclosure, nearest-centerline selection proof, periodic seam ownership, or production root admission."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for row in results:
        print(json.dumps({key: row[key] for key in (
            "member", "span", "t_width_cm", "u_width", "state",
            "contraction_norm_inf") if key in row}))


if __name__ == "__main__":
    main()
