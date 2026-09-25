"""Bounded interval subdivision of the analytic swept-coil seam lead strip.

This is an off-production real-arithmetic model check. It does not enclose the
compiled floating implementation or authorize a swept-surface hit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np

from probe_swept_krawczyk import equations, power_for_span, I


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def intersects_band(value: I, slack: float) -> bool:
    if not (math.isfinite(value.lo) and math.isfinite(value.hi)
            and value.lo <= value.hi):
        return True
    return value.lo <= slack and value.hi >= -slack


def separation_margin(value: I) -> float:
    if value.hi < 0.0:
        return -value.hi
    if value.lo > 0.0:
        return value.lo
    raise ValueError("interval does not exclude zero")


def split_box(box: tuple[float, float, float, float]):
    tlo, thi, ulo, uhi = box
    # Balance variation in the two inputs near a seam crossing.
    axis = 1 if (uhi - ulo) / 1e-4 > (thi - tlo) / 1e-6 else 0
    if axis == 1:
        mid = (ulo + uhi) / 2
        if ulo < mid < uhi:
            return (tlo, thi, ulo, mid), (tlo, thi, mid, uhi)
        axis = 0
    mid = (tlo + thi) / 2
    if tlo < mid < thi:
        return (tlo, mid, ulo, uhi), (mid, thi, ulo, uhi)
    if axis == 0:
        mid = (ulo + uhi) / 2
        if ulo < mid < uhi:
            return (tlo, thi, ulo, mid), (tlo, thi, mid, uhi)
    return None


def check_strip(power: np.ndarray, initial: list[tuple[float, float, float, float]],
                cap: int, ellipse_slack: float,
                stationarity_slack: float) -> dict:
    pending = [(box, 0) for box in initial]
    evaluated = 0
    rejected_ellipse = rejected_stationarity = 0
    deepest = 0
    nonfinite_nodes = 0
    smallest_ellipse_margin = math.inf
    smallest_stationarity_margin = math.inf
    tightest_ellipse_box = None
    tightest_stationarity_box = None
    unresolved = []
    while pending and evaluated < cap:
        box, depth = pending.pop()
        evaluated += 1
        deepest = max(deepest, depth)
        tlo, thi, ulo, uhi = box
        result = equations(power, I(tlo, thi), I(ulo, uhi))
        if any(not (math.isfinite(item.value.lo) and math.isfinite(item.value.hi)
                    and item.value.lo <= item.value.hi) for item in result):
            nonfinite_nodes += 1
        if not intersects_band(result[0].value, ellipse_slack):
            rejected_ellipse += 1
            margin = separation_margin(result[0].value)
            if margin < smallest_ellipse_margin:
                smallest_ellipse_margin = margin
                tightest_ellipse_box = box
            continue
        if not intersects_band(result[1].value, stationarity_slack):
            rejected_stationarity += 1
            margin = separation_margin(result[1].value)
            if margin < smallest_stationarity_margin:
                smallest_stationarity_margin = margin
                tightest_stationarity_box = box
            continue
        pair = split_box(box)
        if pair is None:
            unresolved.append(box)
        else:
            pending.extend((child, depth + 1) for child in pair)
    unresolved.extend(box for box, _ in pending)
    return {"state": "MODEL_STRIP_EXCLUDED" if not unresolved else "UNDECIDED",
            "evaluated_nodes": evaluated, "max_depth": deepest,
            "excluded_by_ellipse": rejected_ellipse,
            "excluded_by_stationarity": rejected_stationarity,
            "smallest_ellipse_margin": (smallest_ellipse_margin
                                        if math.isfinite(smallest_ellipse_margin)
                                        else None),
            "smallest_stationarity_margin_cm2_per_u": (
                smallest_stationarity_margin
                if math.isfinite(smallest_stationarity_margin) else None),
            "tightest_ellipse_box": tightest_ellipse_box,
            "tightest_stationarity_box": tightest_stationarity_box,
            "nonfinite_nodes": nonfinite_nodes,
            "unresolved_count": len(unresolved),
            "unresolved_preview": unresolved[:16],
            "initial_boxes": initial}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--conditioning", type=Path, required=True)
    parser.add_argument("--krawczyk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cap", type=int, default=2000)
    parser.add_argument("--ellipse-slack", type=float, default=0.0)
    parser.add_argument("--stationarity-slack", type=float, default=0.0)
    parser.add_argument("--earlier-gap", type=float)
    args = parser.parse_args()
    if (args.output.exists() or args.cap < 1
            or not math.isfinite(args.ellipse_slack)
            or not math.isfinite(args.stationarity_slack)
            or args.ellipse_slack < 0.0 or args.stationarity_slack < 0.0):
        parser.error("output must be new, cap positive, and slacks finite/nonnegative")
    if args.earlier_gap is not None and not (math.isfinite(args.earlier_gap)
                                            and 0.0 < args.earlier_gap < 1e-5):
        parser.error("earlier gap must be finite and in (0, 1e-5) cm")
    if args.earlier_gap is None and (args.ellipse_slack or args.stationarity_slack):
        parser.error("nonzero slacks require an earlier gap; root-island carving uses exact equations")
    conditioned = json.loads(args.conditioning.read_text())
    certified = json.loads(args.krawczyk.read_text())
    if (conditioned.get("h5_sha256") != sha256(args.h5)
            or certified.get("h5_sha256") != sha256(args.h5)
            or certified.get("conditioning_sha256") != sha256(args.conditioning)):
        raise ValueError("input identities disagree")
    results = []
    with h5py.File(args.h5) as handle:
        for prior in conditioned["results"]:
            member, span = int(prior["member"]), int(prior["span"])
            group = handle[f"coils/coil_{member:03d}"]
            fields = np.column_stack((group["centerline_coefficients"][:],
                                      group["normal_coefficients"][:],
                                      group["major_radius_coefficients"][:],
                                      group["minor_radius_coefficients"][:]))
            power = power_for_span(fields, span)
            native_lead = float(prior["initial_distance_cm"])
            model_root = float(prior["candidate_distance_cm"])
            lower = native_lead - 1e-5
            upper = (native_lead - args.earlier_gap
                     if args.earlier_gap is not None else model_root + 1e-6)
            if not lower < upper:
                raise ValueError("rounded strip bounds are empty")
            initial = [(lower, upper, 0.0, 1.0)]
            known_root = None
            matching = [r for r in certified["results"]
                        if r["member"] == member and r["span"] == span
                        and r["t_width_cm"] == 1e-6]
            if len(matching) != 1:
                raise ValueError("missing unique seam tile receipt")
            tile = matching[0]
            if (args.earlier_gap is None and tile["state"]
                    == "MODEL_UNIQUE_EXISTENCE_CANDIDATE"):
                if not (tile["strict_inside"] and not tile["disjoint"]
                        and tile["contraction_norm_inf"] < 1.0):
                    raise ValueError("invalid root-island receipt")
                tlo, thi = tile["box"][0]
                ulo, uhi = tile["box"][1]
                if not (lower < tlo < thi <= upper and 0.0 < ulo < uhi == 1.0):
                    raise ValueError("root tile does not fit the lead strip")
                known_root = tile["box"]
                initial = [(lower, tlo, 0.0, 1.0),
                           (tlo, thi, 0.0, ulo)]
                if thi < upper:
                    initial.append((thi, upper, 0.0, 1.0))
            outcome = check_strip(power, initial, args.cap,
                                  args.ellipse_slack,
                                  args.stationarity_slack)
            if known_root is not None and outcome["state"] == "MODEL_STRIP_EXCLUDED":
                outcome["state"] = "MODEL_COMPLEMENT_EXCLUDED"
            outcome.update({"member": member, "span": span,
                            "native_lead_cm": native_lead,
                            "model_root_cm": model_root,
                            "strip_cm": [lower, upper],
                            "known_root_box": known_root})
            results.append(outcome)
            print(member, span, outcome["state"],
                  outcome["evaluated_nodes"], outcome["unresolved_count"],
                  flush=True)
    report = {"schema": "stellarcsg.swept-seam-cover-feasibility/v1",
              "state": "EXPERIMENTAL_RECONSTRUCTED_MODEL_ONLY",
              "source_sha256": sha256(Path(__file__)),
              "h5_sha256": sha256(args.h5),
              "conditioning_sha256": sha256(args.conditioning),
              "krawczyk_sha256": sha256(args.krawczyk),
              "node_cap_per_chart": args.cap,
              "ellipse_slack": args.ellipse_slack,
              "stationarity_slack_cm2_per_u": args.stationarity_slack,
              "earlier_gap_cm": args.earlier_gap,
              "results": results,
              "claim_boundary": "Interval subdivision checks only two necessary equations of reconstructed powers. Slacks are hypothetical additive residual bands, not derived C++ floating error bounds. Root island reuses an experimental Krawczyk result. No floating C++ or nearest-centerline enclosure, full-spans proof, or production hit admission."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
