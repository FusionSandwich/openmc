"""Check exact Bernstein convexity margins for compiled seam center powers.

The input strip comes from the stationary-model receipt. All arithmetic in
this audit is rational after loading the binary64 compiled power and strip
endpoints. It does not enclose the C++ long-double coefficient calculation.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controls(power: list[list[Fraction]], ray_distance: Fraction) -> dict:
    query = [Fraction(550) - ray_distance, Fraction(0), Fraction(0)]
    stationary = [Fraction(0) for _ in range(6)]
    term_absolute_sum = [Fraction(0) for _ in range(6)]
    for axis in range(3):
        offset = power[axis].copy()
        offset[0] -= query[axis]
        for i in range(4):
            for j in range(3):
                term = offset[i] * (j + 1) * power[axis][j + 1]
                stationary[i + j] += term
                term_absolute_sum[i + j] += abs(term)
    slope = [stationary[k] * k for k in range(1, 6)]
    bernstein = [
        slope[0],
        slope[0] + slope[1] / 4,
        slope[0] + slope[1] / 2 + slope[2] / 6,
        slope[0] + 3 * slope[1] / 4 + slope[2] / 2 + slope[3] / 4,
        sum(slope),
    ]
    return {"stationary_endpoints": [stationary[0], sum(stationary)],
            "slope": slope, "bernstein": bernstein,
            "term_absolute_sum": term_absolute_sum}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stationary", type=Path, required=True)
    parser.add_argument("--all-spans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    stationarity = json.loads(args.stationary.read_text())
    if stationarity["state"] != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED":
        raise ValueError("unexpected stationary receipt state")
    by_member = {int(row["member"]): row for row in stationarity["results"]}
    rows = []
    for line in args.all_spans.read_text().splitlines():
        record = json.loads(line)
        member = int(record["member"])
        if member not in by_member or int(record["span"]) != int(
                by_member[member]["span"]):
            continue
        power = [[Fraction.from_float(float.fromhex(value))
                  for value in record["power_hex"][axis]]
                 for axis in range(3)]
        strip = [Fraction.from_float(float(value))
                 for value in by_member[member]["distance_strip_cm"]]
        ends = [controls(power, value) for value in strip]
        lower = [min(ends[0]["bernstein"][k],
                     ends[1]["bernstein"][k]) for k in range(5)]
        upper = [max(ends[0]["bernstein"][k],
                     ends[1]["bernstein"][k]) for k in range(5)]
        scale_upper = max(sum(abs(value) for value in end["slope"])
                          for end in ends)
        # x87 long double has epsilon 2^-63; this is only the source-code
        # branch margin evaluated with exact coefficients, not a roundoff proof.
        source_margin_upper = 64 * Fraction(1, 2**63) * scale_upper
        stationary_first = [end["stationary_endpoints"][0] for end in ends]
        stationary_last = [end["stationary_endpoints"][1] for end in ends]
        maximum_absolute_terms = max(sum(end["term_absolute_sum"])
                                     for end in ends)
        conservative_64eps_term_budget = (
            64 * Fraction(1, 2**63) * maximum_absolute_terms)
        rows.append({
            "member": member, "span": record["span"],
            "distance_strip_cm": [float(x) for x in strip],
            "bernstein_lower": [float(x) for x in lower],
            "bernstein_upper": [float(x) for x in upper],
            "minimum_bernstein_lower": float(min(lower)),
            "source_margin_upper_assuming_binary80": float(source_margin_upper),
            "sum_absolute_terms_upper": float(maximum_absolute_terms),
            "conservative_64eps_term_budget": float(
                conservative_64eps_term_budget),
            "stationary_at_zero": [float(min(stationary_first)),
                                   float(max(stationary_first))],
            "stationary_at_one": [float(min(stationary_last)),
                                  float(max(stationary_last))],
            "real_convex_margin_exceeds_source_margin":
                min(lower) > source_margin_upper,
            "real_bracketed_root": max(stationary_first) < 0
                and min(stationary_last) > 0,
        })
    rows.sort(key=lambda row: row["member"])
    if [row["member"] for row in rows] != [2, 3]:
        raise ValueError("missing seam spans")
    achieved = all(row["real_convex_margin_exceeds_source_margin"]
                   and row["real_bracketed_root"] for row in rows)
    receipt = {
        "schema": "stellarcsg.seam-convex-branch-model/v1",
        "state": "REAL_BERNSTEIN_CONVEX_WITH_BRACKETED_ROOT" if achieved
                 else "UNDECIDED",
        "source_sha256": digest(Path(__file__)),
        "stationary_sha256": digest(args.stationary),
        "compiled_all_spans_sha256": digest(args.all_spans),
        "results": rows,
        "claim_boundary": "The exact real degree-five stationary polynomial made from compiled binary64 powers has positive derivative Bernstein controls and opposing endpoint signs over each native-lead strip. The source-code 64-epsilon branch margin is compared under binary80 epsilon, but C++ long-double rounding, root iteration, BVH choice, rounded frame, and implicit surface remain unproved."
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    for row in rows:
        print(row["member"], row["minimum_bernstein_lower"],
              row["source_margin_upper_assuming_binary80"],
              row["conservative_64eps_term_budget"],
              row["stationary_at_zero"], row["stationary_at_one"])
    if not achieved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
