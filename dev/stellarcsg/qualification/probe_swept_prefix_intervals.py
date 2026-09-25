"""Experimental interval-projection feasibility probe for swept ray prefixes.

This uses outward-expanded Python floats on reconstructed spline powers. It is
not a proof of the compiled C++ evaluation path and must not admit a hit.
The probe tests whether interval projection plus adaptive spline subdivision
could eventually supply the missing earlier-root exclusion certificate.
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


@dataclass(frozen=True)
class I:
    lo: float
    hi: float

    @staticmethod
    def point(value: float) -> "I":
        return I(value, value)

    @staticmethod
    def bounds(lo: float, hi: float) -> "I":
        return I(math.nextafter(lo, -math.inf), math.nextafter(hi, math.inf))

    def __add__(self, other: "I") -> "I":
        return I.bounds(self.lo + other.lo, self.hi + other.hi)

    def __neg__(self) -> "I":
        return I(-self.hi, -self.lo)

    def __sub__(self, other: "I") -> "I":
        return self + -other

    def __mul__(self, other: "I") -> "I":
        corners = (self.lo * other.lo, self.lo * other.hi,
                   self.hi * other.lo, self.hi * other.hi)
        if any(math.isnan(value) for value in corners):
            return I(-math.inf, math.inf)
        return I.bounds(min(corners), max(corners))

    def __truediv__(self, other: "I") -> "I":
        if other.lo <= 0.0 <= other.hi:
            return I(-math.inf, math.inf)
        corners = (self.lo / other.lo, self.lo / other.hi,
                   self.hi / other.lo, self.hi / other.hi)
        if any(math.isnan(value) for value in corners):
            return I(-math.inf, math.inf)
        return I.bounds(min(corners), max(corners))

    def square(self) -> "I":
        lo = 0.0 if self.lo <= 0.0 <= self.hi else min(
            self.lo * self.lo, self.hi * self.hi)
        hi = max(self.lo * self.lo, self.hi * self.hi)
        return I.bounds(lo, hi)

    def sqrt(self) -> "I":
        if self.lo < 0.0 or math.isnan(self.hi):
            return I(-math.inf, math.inf)
        return I.bounds(math.sqrt(self.lo), math.sqrt(self.hi))

    def clip_unit(self) -> "I | None":
        lo, hi = max(-1.0, self.lo), min(1.0, self.hi)
        return I(lo, hi) if lo <= hi else None


def dot(a: list[I], b: list[I]) -> I:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: list[I], b: list[I]) -> list[I]:
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def normalized(a: list[I]) -> list[I] | None:
    length = dot(a, a).sqrt()
    if not (length.lo > 0.0 and math.isfinite(length.hi)):
        return None
    return [value / length for value in a]


BASIS_TO_POWER = (
    (1.0 / 6.0, 4.0 / 6.0, 1.0 / 6.0, 0.0),
    (-0.5, 0.0, 0.5, 0.0),
    (0.5, -1.0, 0.5, 0.0),
    (-1.0 / 6.0, 0.5, -0.5, 1.0 / 6.0),
)


def power_for_span(fields: np.ndarray, span: int) -> np.ndarray:
    n = len(fields)
    controls = fields[[(span + a - 1) % n for a in range(4)]]
    power = np.zeros((fields.shape[1], 4), dtype=np.float64)
    for field in range(fields.shape[1]):
        for order in range(4):
            for a in range(4):
                power[field, order] += BASIS_TO_POWER[order][a] * controls[a, field]
    return power


def polynomial(p: np.ndarray, u: I) -> I:
    return ((I.point(float(p[3])) * u + I.point(float(p[2]))) * u
            + I.point(float(p[1]))) * u + I.point(float(p[0]))


def derivative(p: np.ndarray, u: I, scale: float) -> I:
    return ((I.point(float(3.0 * p[3])) * u
             + I.point(float(2.0 * p[2]))) * u
            + I.point(float(p[1]))) * I.point(scale)


def exclude_prefix(power: np.ndarray, u: I, origin_x: float,
                   lead: float, scale: float, prefix_gap: float) -> str:
    center = [polynomial(power[field], u) for field in range(3)]
    tangent = normalized([derivative(power[field], u, scale)
                          for field in range(3)])
    if tangent is None:
        return "undecided_frame"
    supplied = [polynomial(power[field], u) for field in range(3, 6)]
    projection = dot(supplied, tangent)
    normal = normalized([supplied[i] - projection * tangent[i]
                         for i in range(3)])
    if normal is None:
        return "undecided_frame"
    binormal = normalized(cross(tangent, normal))
    if binormal is None:
        return "undecided_frame"
    normal = cross(binormal, tangent)
    major, minor = polynomial(power[6], u), polynomial(power[7], u)
    a_y, a_z = major * normal[1], major * normal[2]
    b_y, b_z = minor * binormal[1], minor * binormal[2]
    cutoff_x = origin_x - lead + prefix_gap
    unit_range = I(-1.0, 1.0)
    def complementary_branches(known: I) -> tuple[I, I]:
        largest = max(abs(known.lo), abs(known.hi))
        squared_upper = math.nextafter(largest * largest, math.inf)
        complement_lower = max(0.0, math.nextafter(
            1.0 - squared_upper, -math.inf))
        lower = math.sqrt(complement_lower)
        lower = max(0.0, math.nextafter(lower, -math.inf))
        return I(-1.0, -lower), I(lower, 1.0)
    def away_from_prefix(x: I) -> bool:
        return x.hi < cutoff_x or x.lo > origin_x
    for offset, a, b in ((center[1], a_y, b_y),
                         (center[2], a_z, b_z)):
        if not (a.lo <= 0.0 <= a.hi):
            cosine_bound = ((-offset - b * unit_range) / a).clip_unit()
            if cosine_bound is None:
                return "excluded_projection"
            x_bound = (center[0] + major * cosine_bound * normal[0]
                       + minor * unit_range * binormal[0])
            if away_from_prefix(x_bound):
                return "excluded_single_equation_prefix"
            if all(away_from_prefix(center[0]
                       + major * cosine_bound * normal[0]
                       + minor * branch * binormal[0])
                   for branch in complementary_branches(cosine_bound)):
                return "excluded_unit_branches"
        if not (b.lo <= 0.0 <= b.hi):
            sine_bound = ((-offset - a * unit_range) / b).clip_unit()
            if sine_bound is None:
                return "excluded_projection"
            x_bound = (center[0] + major * unit_range * normal[0]
                       + minor * sine_bound * binormal[0])
            if away_from_prefix(x_bound):
                return "excluded_single_equation_prefix"
            if all(away_from_prefix(center[0]
                       + major * branch * normal[0]
                       + minor * sine_bound * binormal[0])
                   for branch in complementary_branches(sine_bound)):
                return "excluded_unit_branches"
    det = a_y * b_z - b_y * a_z
    if det.lo <= 0.0 <= det.hi:
        return "undecided_projection"
    rhs_y, rhs_z = -center[1], -center[2]
    cosine = ((rhs_y * b_z - b_y * rhs_z) / det).clip_unit()
    sine = ((a_y * rhs_z - rhs_y * a_z) / det).clip_unit()
    if cosine is None or sine is None:
        return "excluded_projection"
    unit = cosine.square() + sine.square()
    if unit.hi < 1.0 or unit.lo > 1.0:
        return "excluded_unit_circle"
    x = center[0] + major * cosine * normal[0] + minor * sine * binormal[0]
    if x.hi < cutoff_x or x.lo > origin_x:
        return "excluded_ray_prefix"
    return "undecided_root"


def analyze_span(power: np.ndarray, origin_x: float, lead: float,
                 scale: float, prefix_gap: float,
                 max_depth: int, max_nodes: int) -> dict:
    stack = [(0.0, 1.0, 0)]
    outcome: dict[str, int] = {}
    undecided_leaves = []
    nodes = 0
    while stack:
        lo, hi, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            outcome["budget_exhausted"] = outcome.get("budget_exhausted", 0) + 1
            break
        state = exclude_prefix(power, I.bounds(lo, hi), origin_x, lead,
                               scale, prefix_gap)
        if state.startswith("excluded_") or depth == max_depth:
            outcome[state] = outcome.get(state, 0) + 1
            if not state.startswith("excluded_"):
                undecided_leaves.append({"u_min": lo, "u_max": hi,
                                         "reason": state})
            continue
        midpoint = 0.5 * (lo + hi)
        stack.extend([(midpoint, hi, depth + 1),
                      (lo, midpoint, depth + 1)])
    return {"nodes": nodes, "outcomes": outcome,
            "undecided_leaves": undecided_leaves,
            "fully_excluded": all(name.startswith("excluded_")
                                  for name in outcome)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--max-nodes", type=int, default=10000)
    parser.add_argument("--prefix-gap-cm", type=float, default=0.0)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    if not math.isfinite(args.prefix_gap_cm) or args.prefix_gap_cm < 0.0:
        parser.error("prefix gap must be finite and nonnegative")
    receipt = json.loads(args.native_receipt.read_text())
    h5_hash = hashlib.sha256(args.h5.read_bytes()).hexdigest()
    matching_hashes = [value for path, value in receipt["hashes"].items()
                       if Path(path).name == args.h5.name]
    if matching_hashes != [h5_hash]:
        raise ValueError("native receipt binds a different HDF5")
    probes = receipt["solver_probes"]
    rows = []
    negative_control = {}
    with h5py.File(args.h5) as h5:
        for probe in probes:
            member = int(probe["member"])
            lead = float(probe["lead_distance_cm"])
            group = h5["coils"][f"coil_{member:03d}"]
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            n = len(fields)
            radii = np.maximum(fields[:, 6], fields[:, 7])
            ids = (np.arange(n)[:, None] + np.arange(-1, 3)) % n
            center = fields[ids, :3]
            radius = radii[ids].max(axis=1)
            lower = center.min(axis=1) - radius[:, None]
            upper = center.max(axis=1) + radius[:, None]
            possible = ((lower[:, 1] <= 0.0) & (upper[:, 1] >= 0.0)
                        & (lower[:, 2] <= 0.0) & (upper[:, 2] >= 0.0)
                        & (upper[:, 0] >= 550.0 - lead))
            for span in np.flatnonzero(possible):
                result = analyze_span(power_for_span(fields, int(span)),
                                      550.0, lead, n / (2.0 * math.pi),
                                      args.prefix_gap_cm,
                                      args.max_depth, args.max_nodes)
                rows.append({"member": member, "span": int(span), **result})
            # A later cutoff encloses the known lead. At least one span must
            # stay undecided, or this exclusion experiment is unsound here.
            control = [analyze_span(power_for_span(fields, int(span)),
                                    550.0, lead + 4.0,
                                    n / (2.0 * math.pi), 0.0,
                                    args.max_depth, args.max_nodes)
                       for span in np.flatnonzero(possible)]
            negative_control[member] = {
                "lead_plus_cm": 4.0,
                "undecided_spans": int(sum(not item["fully_excluded"]
                                            for item in control)),
            }
            if negative_control[member]["undecided_spans"] == 0:
                raise RuntimeError("known-root negative control was excluded")
    report = {"schema": "stellarcsg.swept-prefix-interval-probe/v1",
              "h5_sha256": h5_hash,
              "native_receipt_sha256": hashlib.sha256(
                  args.native_receipt.read_bytes()).hexdigest(),
              "max_depth": args.max_depth, "max_nodes": args.max_nodes,
              "prefix_gap_cm": args.prefix_gap_cm,
              "rows": rows, "negative_control": negative_control,
              "claim_boundary": "Feasibility probe only: reconstructed Python powers and interval arithmetic are not a C++ execution proof; candidate-root isolation and exact nearest-root ordering remain unproved; no terminal unresolved status is cleared."}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"spans": len(rows),
                      "fully_excluded": sum(row["fully_excluded"] for row in rows),
                      "nodes": sum(row["nodes"] for row in rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
