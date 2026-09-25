"""Enclose the local centerline minimum across analytic seam lead strips.

This proves a statement about real polynomials with stored binary64 powers.
It does not certify the compiled nearest-centerline algorithm or global choice.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np

from probe_swept_prefix_intervals import I, polynomial, power_for_span


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def enclosed_product(a: float, b: float) -> I:
    # A single rounded product with one outward step encloses its exact value.
    product = a * b
    return I.bounds(product, product)


def stationarity(power: np.ndarray, t: I, u: I) -> tuple[I, I]:
    center = [polynomial(power[field], u) for field in range(3)]
    first = []
    second = []
    for field in range(3):
        p = power[field]
        c1 = I.point(float(p[1]))
        twice_c2 = enclosed_product(2.0, float(p[2]))
        thrice_c3 = enclosed_product(3.0, float(p[3]))
        six_c3 = enclosed_product(6.0, float(p[3]))
        first.append((thrice_c3 * u + twice_c2) * u + c1)
        second.append(six_c3 * u + twice_c2)
    offset = [I.point(550.0) - t - center[0], -center[1], -center[2]]
    value = sum((offset[i] * first[i] for i in range(3)), I.point(0.0))
    derivative = sum((offset[i] * second[i] - first[i].square()
                      for i in range(3)), I.point(0.0))
    return value, derivative


def pair(value: I) -> list[float]:
    return [value.lo, value.hi]


def fused_round(a: float, b: float, c: float) -> float:
    exact = (Fraction.from_float(a) * Fraction.from_float(b)
             + Fraction.from_float(c))
    return float(exact)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--conditioning", type=Path, required=True)
    parser.add_argument("--compiled-spans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    conditioning = json.loads(args.conditioning.read_text())
    compiled = json.loads(args.compiled_spans.read_text())
    h5_hash = sha256(args.h5)
    if (conditioning.get("h5_sha256") != h5_hash
            or compiled.get("h5_sha256") != h5_hash
            or compiled.get("state")
            != "COMPILED_SEAM_POWERS_MATCH_MODEL_BITWISE"):
        raise ValueError("conditioned/compiled/HDF5 identities disagree")
    results = []
    with h5py.File(args.h5) as handle:
        for prior in conditioning["results"]:
            member, span = int(prior["member"]), int(prior["span"])
            group = handle[f"coils/coil_{member:03d}"]
            if span != len(group["centerline_coefficients"]) - 1:
                continue
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            power = power_for_span(fields, span)
            rows = [item for item in compiled["compiled_spans"]
                    if item["member"] == member and item["span"] == span]
            if len(rows) != 1:
                raise ValueError("missing compiled last span")
            row = rows[0]
            if any(float(power[field, degree]).hex()
                   != float.fromhex(row["power_hex"][field][degree]).hex()
                   for field in range(8) for degree in range(4)):
                raise ValueError("stored powers differ from compiled span")
            native_lead = float(prior["initial_distance_cm"])
            model_root = float(prior["candidate_distance_cm"])
            distance = I(native_lead - 1e-5, model_root + 1e-6)
            parameter = I(1.0 - 1e-8, 1.0)
            left, _ = stationarity(power, distance, I.point(parameter.lo))
            right, _ = stationarity(power, distance, I.point(1.0))
            _, slope = stationarity(power, distance, parameter)
            if not (math.isfinite(left.lo) and math.isfinite(right.hi)
                    and math.isfinite(slope.lo) and math.isfinite(slope.hi)
                    and left.lo > 0.0 and right.hi < 0.0 and slope.hi < 0.0):
                raise ValueError("uniform local minimum signs not established")
            root = I.point(1.0) - right / slope
            if not (parameter.lo < root.lo < root.hi < 1.0):
                raise ValueError("stationary root enclosure escaped tile")
            angle_min = float.fromhex(row["angle_min_hex"])
            angle_max = float.fromhex(row["angle_max_hex"])
            width = angle_max - angle_min
            separate = [angle_min + u * width for u in (root.lo, root.hi)]
            fused = [fused_round(u, width, angle_min)
                     for u in (root.lo, root.hi)]
            same_angle_cell = (separate[0] == separate[1]
                               == fused[0] == fused[1])
            results.append({
                "member": member, "span": span,
                "native_lead_cm": native_lead,
                "model_root_cm": model_root,
                "distance_strip_cm": pair(distance),
                "parameter_tile": pair(parameter),
                "stationarity_at_tile_left": pair(left),
                "stationarity_at_tile_right": pair(right),
                "stationarity_u_derivative": pair(slope),
                "uniform_local_minimum": True,
                "stationary_u_enclosure": pair(root),
                "separate_round_angle_hex": [value.hex()
                                              for value in separate],
                "fused_round_angle_hex": [value.hex() for value in fused],
                "same_angle_cell_for_exact_root": same_angle_cell,
            })
            print(member, pair(root), separate[0].hex(), same_angle_cell)
    if len(results) != 2:
        raise ValueError("expected two shaped last spans")
    report = {"schema": "stellarcsg.seam-stationarity-interval/v1",
              "state": "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED",
              "source_sha256": sha256(Path(__file__)),
              "h5_sha256": h5_hash,
              "conditioning_sha256": sha256(args.conditioning),
              "compiled_spans_sha256": sha256(args.compiled_spans),
              "results": results,
              "claim_boundary": "For each ray distance in the stated strip, the real stored-power last-span centerline has exactly one local squared-distance minimum within the stated u tile. Mapping that exact root through the source angle expression selects the reported binary64 cell under separate and fused arithmetic. This does not bound the numerical nearest-root algorithm, prove global nearest selection across spans, enclose C++ frame/evaluate rounding, or admit a production hit."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
