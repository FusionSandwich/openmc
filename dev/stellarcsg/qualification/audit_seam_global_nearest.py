"""Screen every analytic centerline span for the seam ray-distance strip.

The proof target is the real continuous centerline represented by stored
binary64 powers, not the compiled nearest-root algorithm or implicit surface.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import h5py

from audit_seam_stationarity import stationarity
from probe_swept_prefix_intervals import I, polynomial, power_for_span


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance_squared(power, distance: I, parameter: I) -> I:
    center = [polynomial(power[field], parameter) for field in range(3)]
    offset = [I.point(550.0) - distance - center[0],
              -center[1], -center[2]]
    return sum((value.square() for value in offset), I.point(0.0))


def partition(power, distance: I, candidate_upper: float,
              maximum_nodes: int) -> dict:
    pending = [(0.0, 1.0, 0)]
    nodes = 0
    excluded = 0
    min_margin = math.inf
    max_depth = 0
    unresolved = []
    while pending and nodes < maximum_nodes:
        lo, hi, depth = pending.pop()
        nodes += 1
        max_depth = max(max_depth, depth)
        bound = distance_squared(power, distance, I(lo, hi))
        if math.isfinite(bound.lo) and bound.lo > candidate_upper:
            excluded += 1
            min_margin = min(min_margin, bound.lo - candidate_upper)
            continue
        midpoint = (lo + hi) / 2.0
        if not lo < midpoint < hi:
            unresolved.append([lo, hi])
        else:
            pending.extend(((lo, midpoint, depth + 1),
                            (midpoint, hi, depth + 1)))
    unresolved.extend([lo, hi] for lo, hi, _ in pending)
    return {"nodes": nodes, "max_depth": max_depth,
            "excluded_tiles": excluded,
            "minimum_exclusion_margin_cm2": (min_margin
                                              if math.isfinite(min_margin)
                                              else None),
            "unresolved_tiles": len(unresolved),
            "unresolved_preview": unresolved[:8]}


def stationarity_sign(power, distance: I, upper: float,
                      expected_sign: int, maximum_nodes: int) -> dict:
    pending = [(0.0, upper, 0)]
    nodes = 0
    min_margin = math.inf
    max_depth = 0
    unresolved = []
    while pending and nodes < maximum_nodes:
        lo, hi, depth = pending.pop()
        nodes += 1
        max_depth = max(max_depth, depth)
        value, _ = stationarity(power, distance, I(lo, hi))
        margin = (value.lo if expected_sign > 0 else -value.hi)
        if math.isfinite(margin) and margin > 0.0:
            min_margin = min(min_margin, margin)
            continue
        midpoint = (lo + hi) / 2.0
        if not lo < midpoint < hi:
            unresolved.append([lo, hi])
        else:
            pending.extend(((lo, midpoint, depth + 1),
                            (midpoint, hi, depth + 1)))
    unresolved.extend([lo, hi] for lo, hi, _ in pending)
    return {"nodes": nodes, "max_depth": max_depth,
            "minimum_sign_margin_cm2_per_u": (min_margin
                                               if math.isfinite(min_margin)
                                               else None),
            "unresolved_tiles": len(unresolved),
            "unresolved_preview": unresolved[:8]}


def exact_endpoint_delta(first_power, last_power,
                         distance: I) -> dict:
    first = [Fraction.from_float(float(first_power[field, 0]))
             for field in range(3)]
    last = [sum((Fraction.from_float(float(last_power[field, order]))
                 for order in range(4)), Fraction(0)) for field in range(3)]

    def squared(center: list[Fraction], t: float) -> Fraction:
        ray_x = Fraction(550) - Fraction.from_float(t)
        return ((ray_x - center[0]) ** 2 + center[1] ** 2
                + center[2] ** 2)

    values = [squared(last, t) - squared(first, t)
              for t in (distance.lo, distance.hi)]
    lower, upper = min(values), max(values)
    return {"range_cm2": [float(lower), float(upper)],
            "exact_upper_cm2": str(upper),
            "strictly_negative": upper < 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--stationary", type=Path, required=True)
    parser.add_argument("--compiled-spans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cap-per-span", type=int, default=256)
    parser.add_argument("--cap-sign", type=int, default=10000)
    args = parser.parse_args()
    if args.output.exists() or args.cap_per_span < 1 or args.cap_sign < 1:
        parser.error("output must be new and caps positive")
    stationary = json.loads(args.stationary.read_text())
    compiled = json.loads(args.compiled_spans.read_text())
    h5_hash = sha256(args.h5)
    if (stationary.get("state") != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED"
            or stationary.get("h5_sha256") != h5_hash
            or compiled.get("h5_sha256") != h5_hash
            or stationary.get("compiled_spans_sha256")
            != sha256(args.compiled_spans)):
        raise ValueError("stationary/compiled/HDF5 identities disagree")
    results = []
    with h5py.File(args.h5) as handle:
        for prior in stationary["results"]:
            member = int(prior["member"])
            controls = handle[f"coils/coil_{member:03d}"][
                "centerline_coefficients"][:]
            count = len(controls)
            if prior["span"] != count - 1:
                raise ValueError("stationary report is not last span")
            distance = I(*prior["distance_strip_cm"])
            powers = [power_for_span(controls, span)
                      for span in range(count)]
            for span in (0, count - 1):
                matches = [row for row in compiled["compiled_spans"]
                           if row["member"] == member and row["span"] == span]
                if len(matches) != 1 or any(
                        float(powers[span][field, order]).hex()
                        != float.fromhex(matches[0]["power_hex"][field][order]).hex()
                        for field in range(3) for order in range(4)):
                    raise ValueError("compiled seam center powers differ")
            candidate = distance_squared(powers[-1], distance, I.point(1.0))
            if not math.isfinite(candidate.hi):
                raise ValueError("candidate squared distance is nonfinite")
            spans = [partition(power, distance, candidate.hi,
                               args.cap_per_span) for power in powers]
            survivors = [span for span, result in enumerate(spans)
                         if result["unresolved_tiles"]]
            first_sign = stationarity_sign(powers[0], distance, 1.0,
                                           -1, args.cap_sign)
            last_sign = stationarity_sign(powers[-1], distance,
                                          prior["parameter_tile"][0],
                                          +1, args.cap_sign)
            endpoint_delta = exact_endpoint_delta(powers[0], powers[-1],
                                                  distance)
            admitted_model = (survivors == [0, count - 1]
                              and first_sign["unresolved_tiles"] == 0
                              and last_sign["unresolved_tiles"] == 0
                              and endpoint_delta["strictly_negative"]
                              and prior["uniform_local_minimum"] is True)
            results.append({"member": member, "sample_count": count,
                            "distance_strip_cm": [distance.lo, distance.hi],
                            "last_endpoint_candidate_d2_cm2": [candidate.lo,
                                                                candidate.hi],
                            "total_distance_nodes": sum(row["nodes"]
                                                        for row in spans),
                            "excluded_span_count": count - len(survivors),
                            "survivor_spans": survivors,
                            "survivor_details": {str(span): spans[span]
                                                 for span in survivors},
                            "minimum_other_span_margin_cm2": min(
                                row["minimum_exclusion_margin_cm2"]
                                for span, row in enumerate(spans)
                                if span not in survivors),
                            "first_span_stationarity_negative": first_sign,
                            "last_span_stationarity_positive_before_tile": last_sign,
                            "last_minus_first_endpoint_d2_cm2": endpoint_delta,
                            "real_model_global_nearest_last_span": admitted_model})
            print(member, survivors,
                  results[-1]["total_distance_nodes"], endpoint_delta,
                  admitted_model, flush=True)
    if len(results) != 2:
        raise ValueError("expected two shaped members")
    achieved = all(row["real_model_global_nearest_last_span"]
                   for row in results)
    report = {"schema": "stellarcsg.seam-global-nearest-model/v1",
              "state": ("REAL_MODEL_GLOBAL_NEAREST_LAST_SPAN" if achieved
                        else "UNDECIDED"),
              "source_sha256": sha256(Path(__file__)),
              "h5_sha256": h5_hash,
              "stationary_sha256": sha256(args.stationary),
              "compiled_spans_sha256": sha256(args.compiled_spans),
              "cap_per_span": args.cap_per_span,
              "cap_sign": args.cap_sign,
              "results": results,
              "claim_boundary": "Outward polynomial intervals eliminate all other represented real centerline spans; interval stationarity signs and exact rational seam endpoint comparisons select the last-span local minimum for every ray distance in each strip. Only first/last compiled powers were checked bitwise; all other powers use the HDF5 reconstruction. This does not certify the compiled nearest-root algorithm, its BVH pruning, rounded frame/evaluate path, root completeness for arbitrary rays, or a native hit."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not achieved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
