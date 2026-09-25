"""Check binary80 convexity branch margins for compiled seam center powers.

All arithmetic in this audit is rational after loading binary64 inputs. It
accounts for the rounded binary64 ray point and bounds ordinary binary80
round-to-nearest operations in the source stationary/convexity calculation.
It does not bound the subsequent Newton iteration or nearest-span traversal.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controls(power: list[list[Fraction]], query_x: Fraction) -> dict:
    query = [query_x, Fraction(0), Fraction(0)]
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
    parser.add_argument("--all-spans-receipt", type=Path, required=True)
    parser.add_argument("--compiler-macros", type=Path, required=True)
    parser.add_argument("--cmake-cache", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    macros = args.compiler_macros.read_text()
    cache = args.cmake_cache.read_text()
    if ("#define __LDBL_MANT_DIG__ 64" not in macros
            or "#define __FLT_EVAL_METHOD__ 0" not in macros
            or "#define __LDBL_EPSILON__ 1.08420217248550443400745280086994171e-19L"
            not in macros):
        raise ValueError("compiler macro contract differs from binary80")
    flags = next((line.split("=", 1)[1] for line in cache.splitlines()
                  if line.startswith("CMAKE_CXX_FLAGS_RELEASE:STRING=")), None)
    if flags is None or "-O3" not in flags or any(
            option in flags for option in ("-ffast-math", "-Ofast")):
        raise ValueError("unexpected optimization or fast-math flags")
    stationarity = json.loads(args.stationary.read_text())
    all_spans_receipt = json.loads(args.all_spans_receipt.read_text())
    if stationarity["state"] != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED":
        raise ValueError("unexpected stationary receipt state")
    if (all_spans_receipt["state"]
            != "ALL_ANALYTIC_SHAPED_SPANS_BITWISE_IDENTICAL"
            or all_spans_receipt["raw_output_sha256"]
            != digest(args.all_spans)
            or all_spans_receipt["h5_sha256"]
            != stationarity["h5_sha256"]
            or all_spans_receipt["seam_identity_sha256"]
            != stationarity["compiled_spans_sha256"]):
        raise ValueError("compiled power/HDF5/stationary identities differ")
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
        strip = [float(value)
                 for value in by_member[member]["distance_strip_cm"]]
        # IEEE subtraction is monotone. Every compiled ray point formed as
        # 550.0 - t, t in the strip, lies between these rounded endpoints.
        query_x = [Fraction.from_float(550.0 - strip[1]),
                   Fraction.from_float(550.0 - strip[0])]
        if not (query_x[1] / 2 <= power[0][0] <= 2 * query_x[0]):
            raise ValueError("x offset subtraction lacks Sterbenz range")
        ends = [controls(power, value) for value in query_x]
        lower = [min(ends[0]["bernstein"][k],
                     ends[1]["bernstein"][k]) for k in range(5)]
        upper = [max(ends[0]["bernstein"][k],
                     ends[1]["bernstein"][k]) for k in range(5)]
        scale_upper = max(sum(abs(value) for value in end["slope"])
                          for end in ends)
        # GCC/x86-64 binary80 long double has epsilon 2^-63. Each stationary
        # coefficient has at most nine terms, two rounded multiplications per
        # term, and at most eight rounded additions. Its error is below
        # 32*epsilon times the sum of absolute exact terms. The x offset
        # subtraction is exact by Sterbenz in these two strips; other offset
        # subtractions are by zero. The five-term Horner endpoint sum is then
        # within 64*epsilon*S. Formation of derivative slope, Bernstein
        # controls and the source 64*epsilon*scale test is conservatively
        # covered together by 2048*epsilon*S. Values are normal and finite.
        epsilon = Fraction(1, 2**63)
        source_margin_upper = 64 * epsilon * scale_upper
        stationary_first = [end["stationary_endpoints"][0] for end in ends]
        stationary_last = [end["stationary_endpoints"][1] for end in ends]
        maximum_absolute_terms = max(sum(end["term_absolute_sum"])
                                     for end in ends)
        conservative_64eps_term_budget = 64 * epsilon * maximum_absolute_terms
        binary80_branch_budget = 2048 * epsilon * maximum_absolute_terms
        rows.append({
            "member": member, "span": record["span"],
            "distance_strip_cm": strip,
            "rounded_query_x_cm": [float(x) for x in query_x],
            "bernstein_lower": [float(x) for x in lower],
            "bernstein_upper": [float(x) for x in upper],
            "minimum_bernstein_lower": float(min(lower)),
            "source_margin_upper_assuming_binary80": float(source_margin_upper),
            "sum_absolute_terms_upper": float(maximum_absolute_terms),
            "conservative_64eps_term_budget": float(
                conservative_64eps_term_budget),
            "binary80_branch_budget": float(binary80_branch_budget),
            "stationary_at_zero": [float(min(stationary_first)),
                                   float(max(stationary_first))],
            "stationary_at_one": [float(min(stationary_last)),
                                  float(max(stationary_last))],
            "real_convex_margin_exceeds_source_margin":
                min(lower) > source_margin_upper,
            "real_bracketed_root": max(stationary_first) < 0
                and min(stationary_last) > 0,
            "binary80_convex_branch_and_bracket_stable": (
                min(lower) > binary80_branch_budget
                and max(stationary_first) < -conservative_64eps_term_budget
                and min(stationary_last) > conservative_64eps_term_budget),
        })
    rows.sort(key=lambda row: row["member"])
    if [row["member"] for row in rows] != [2, 3]:
        raise ValueError("missing seam spans")
    achieved = all(row["binary80_convex_branch_and_bracket_stable"]
                   for row in rows)
    receipt = {
        "schema": "stellarcsg.seam-convex-branch-model/v2",
        "state": "BINARY80_CONVEX_BRANCH_AND_BRACKET_STABLE" if achieved
                 else "UNDECIDED",
        "source_sha256": digest(Path(__file__)),
        "stationary_sha256": digest(args.stationary),
        "compiled_all_spans_sha256": digest(args.all_spans),
        "compiled_all_spans_receipt_sha256": digest(args.all_spans_receipt),
        "compiler_macros_sha256": digest(args.compiler_macros),
        "cmake_cache_sha256": digest(args.cmake_cache),
        "production_source_sha256": digest(args.production_source),
        "current_standalone_library_sha256": digest(args.library),
        "cxx_release_flags": flags,
        "results": rows,
        "claim_boundary": "For every binary64 ray x formed by rounding 550-t over either seam strip, the exact stored-power stationary polynomial has convex Bernstein controls and opposing endpoint signs. Under GCC/x86-64 binary80 round-to-nearest ordinary operations and the recorded source expression order, conservative 2048-epsilon and 64-epsilon term-sum budgets keep the compiled convexity decision and endpoint bracket unchanged. This does not certify Newton iteration, BVH selection, rounded frame/implicit continuity, or a native hit."
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    for row in rows:
        print(row["member"], row["minimum_bernstein_lower"],
              row["binary80_branch_budget"],
              row["conservative_64eps_term_budget"],
              row["stationary_at_zero"], row["stationary_at_one"])
    if not achieved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
