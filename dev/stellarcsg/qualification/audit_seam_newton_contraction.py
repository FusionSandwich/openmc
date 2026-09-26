"""Bound the real safeguarded Newton loop for analytic seam spans.

Uses exact rational stored powers, Bernstein derivative bounds, and the
rounded binary64 query-x range. It proves a real-arithmetic loop theorem;
binary80 loop rounding and final rounded distance ranking remain separate.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from math import comb
from pathlib import Path

import probe_seam_newton_iterates as newton_model
from probe_seam_newton_iterates import I, stationary


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bernstein(power: list[Fraction]) -> list[Fraction]:
    degree = len(power) - 1
    return [sum((Fraction(comb(i, j), comb(degree, j)) * power[j]
                 for j in range(i + 1)), Fraction(0))
            for i in range(degree + 1)]


def restricted_power(power: list[Fraction], a: Fraction,
                     b: Fraction) -> list[Fraction]:
    h = b - a
    degree = len(power) - 1
    return [sum((power[k] * comb(k, j) * a ** (k - j) * h ** j
                 for k in range(j, degree + 1)), Fraction(0))
            for j in range(degree + 1)]


def controls_at(power: list[list[Fraction]], query_x: Fraction) -> dict:
    coefficients = [item.lo for item in stationary(
        power, I.point(query_x))]
    slope = [k * coefficients[k] for k in range(1, 6)]
    curvature = [k * (k - 1) * coefficients[k]
                 for k in range(2, 6)]
    return {"stationary": coefficients,
            "slope_bernstein": bernstein(slope),
            "curvature_bernstein": bernstein(curvature),
            "curvature_power": curvature}


def float_pair(lo: Fraction, hi: Fraction) -> list[float]:
    return [float(lo), float(hi)]


def fused_round(a: float, b: float, c: float) -> float:
    return float(Fraction.from_float(a) * Fraction.from_float(b)
                 + Fraction.from_float(c))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stationary", type=Path, required=True)
    parser.add_argument("--all-spans", type=Path, required=True)
    parser.add_argument("--all-spans-receipt", type=Path, required=True)
    parser.add_argument("--convex-branch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    stationary_receipt = json.loads(args.stationary.read_text())
    all_spans_receipt = json.loads(args.all_spans_receipt.read_text())
    convex = json.loads(args.convex_branch.read_text())
    if (stationary_receipt["state"]
            != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED"
            or all_spans_receipt["state"]
            != "ALL_ANALYTIC_SHAPED_SPANS_BITWISE_IDENTICAL"
            or all_spans_receipt["raw_output_sha256"] != sha256(args.all_spans)
            or convex["state"]
            != "BINARY80_CONVEX_BRANCH_AND_BRACKET_STABLE"
            or convex["stationary_sha256"] != sha256(args.stationary)
            or convex["compiled_all_spans_sha256"] != sha256(args.all_spans)):
        raise ValueError("input identities or states differ")
    by_member = {int(row["member"]): row
                 for row in stationary_receipt["results"]}
    results = []
    for line in args.all_spans.read_text().splitlines():
        record = json.loads(line)
        member = int(record["member"])
        if member not in by_member or record["span"] != by_member[member]["span"]:
            continue
        power = [[Fraction.from_float(float.fromhex(value))
                  for value in record["power_hex"][axis]]
                 for axis in range(3)]
        tlo, thi = by_member[member]["distance_strip_cm"]
        xlo, xhi = (Fraction.from_float(550.0 - thi),
                    Fraction.from_float(550.0 - tlo))
        ends = [controls_at(power, x) for x in (xlo, xhi)]
        slope_controls = [value for end in ends
                          for value in end["slope_bernstein"]]
        curvature_controls = [value for end in ends
                              for value in end["curvature_bernstein"]]
        m, M = min(slope_controls), max(slope_controls)
        K = max(abs(value) for value in curvature_controls)
        if not (0 < m <= M and K > 0):
            raise ValueError("positive derivative/curvature bound missing")
        f1 = [sum(end["stationary"]) for end in ends]
        f1lo, f1hi = min(f1), max(f1)
        if f1lo <= 0:
            raise ValueError("stationary endpoint bracket missing")
        rlo = 1 - f1hi / m
        rhi = 1 - f1lo / M
        c = K / (2 * m)
        if not (Fraction(1, 2) < rlo <= rhi < 1 and c < 1):
            raise ValueError("root or contraction bound invalid")
        first_interior_n = None
        for n in range(1, 65):
            u = 1 - Fraction(1, 2**n)
            if u < rlo and rhi + c * (rhi - u) ** 2 < 1:
                first_interior_n = n
                break
        if first_interior_n is None:
            raise ValueError("no guaranteed interior Newton step")
        # First accepted Newton update is at most c/4 from the root because
        # any preceding midpoint is in [.5,r]. Fixed curvature sign in that
        # neighborhood makes every subsequent Newton update stay in the
        # current bracket and on the same side of the root.
        errors = [c / 4]
        for _ in range(2):
            errors.append(c * errors[-1] ** 2)
        stable_left = rlo - errors[0]
        stable_right = Fraction(1)
        restricted = [bernstein(restricted_power(
            end["curvature_power"], stable_left, stable_right))
            for end in ends]
        curvature_near = [value for group in restricted for value in group]
        stable_sign = (min(curvature_near) > 0
                       or max(curvature_near) < 0)
        final_lo, final_hi = rlo - errors[-1], rhi + errors[-1]
        angle_min = float.fromhex(record["angle_min_hex"])
        angle_max = float.fromhex(record["angle_max_hex"])
        width = angle_max - angle_min
        separate = [angle_min + float(u) * width
                    for u in (final_lo, final_hi)]
        fused = [fused_round(float(u), width, angle_min)
                 for u in (final_lo, final_hi)]
        expected_angle = by_member[member]["separate_round_angle_hex"][0]
        same_angle = (all(value.hex() == expected_angle
                          for value in separate + fused))
        admitted = (stable_sign and same_angle
                    and first_interior_n + 3 < 80)
        results.append({
            "member": member, "span": record["span"],
            "rounded_query_x_cm": float_pair(xlo, xhi),
            "stationary_slope_global": float_pair(m, M),
            "stationary_curvature_global": float_pair(
                min(curvature_controls), max(curvature_controls)),
            "newton_error_factor_upper": float(c),
            "root_u_enclosure": float_pair(rlo, rhi),
            "root_gap_to_one": float_pair(1 - rhi, 1 - rlo),
            "root_gap_to_one_exact": [str(1 - rhi), str(1 - rlo)],
            "first_guaranteed_interior_dyadic_n": first_interior_n,
            "first_accepted_error_upper": float(errors[0]),
            "second_accepted_error_upper": float(errors[1]),
            "third_accepted_error_upper": float(errors[2]),
            "near_root_curvature": float_pair(
                min(curvature_near), max(curvature_near)),
            "near_root_curvature_fixed_sign": stable_sign,
            "final_u_enclosure": float_pair(final_lo, final_hi),
            "final_gap_to_one": float_pair(1 - final_hi, 1 - final_lo),
            "expected_angle_hex": expected_angle,
            "separate_angle_hex": [value.hex() for value in separate],
            "fused_angle_hex": [value.hex() for value in fused],
            "three_accepted_steps_share_angle_cell": same_angle,
            "real_loop_angle_cell_bound": admitted,
        })
    results.sort(key=lambda row: row["member"])
    if [row["member"] for row in results] != [2, 3]:
        raise ValueError("expected two last seam spans")
    achieved = all(row["real_loop_angle_cell_bound"] for row in results)
    report = {
        "schema": "stellarcsg.seam-newton-contraction/v1",
        "state": "REAL_SAFEGUARDED_NEWTON_REACHES_ANGLE_CELL" if achieved
                 else "UNDECIDED",
        "source_sha256": sha256(Path(__file__)),
        "stationary_helper_sha256": sha256(Path(newton_model.__file__)),
        "stationary_sha256": sha256(args.stationary),
        "compiled_all_spans_sha256": sha256(args.all_spans),
        "compiled_all_spans_receipt_sha256": sha256(args.all_spans_receipt),
        "convex_branch_sha256": sha256(args.convex_branch),
        "results": results,
        "claim_boundary": "Exact rational Bernstein bounds make stationary slope positive on [0,1], bound absolute curvature, and enclose each root from the endpoint residual. The first accepted Newton step is guaranteed by the listed dyadic midpoint; any earlier accepted step contracts. Fixed curvature sign around the root keeps subsequent real Newton steps inside the bracket. After three accepted steps the real parameter maps to the reported binary64 angle cell under separate or fused angle arithmetic. This does not enclose binary80 iteration rounding, floating distance comparison, BVH selection, rounded frame/implicit evaluation, earlier surface roots, or a native hit."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in results:
        print(row["member"], row["first_guaranteed_interior_dyadic_n"],
              row["newton_error_factor_upper"],
              row["near_root_curvature"],
              row["three_accepted_steps_share_angle_cell"],
              row["real_loop_angle_cell_bound"])
    if not achieved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
