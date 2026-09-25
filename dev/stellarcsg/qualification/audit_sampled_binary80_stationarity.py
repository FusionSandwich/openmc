"""Check exact stationary residuals at sampled binary80 seam Newton outputs.

The diagnostic prints 21 significant decimal digits for a binary80 value
in [.5,1). Rounding that decimal to the 2^-64 grid recovers its binary80
parameter when the print error is below 1e-20, which is checked here.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import audit_seam_newton_contraction as contraction_model
import probe_seam_newton_iterates as stationary_model
from audit_seam_newton_contraction import controls_at
from probe_seam_newton_iterates import I, polynomial, stationary


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recover_binary80(decimal_text: str) -> tuple[Fraction, Fraction]:
    printed = Fraction(Decimal(decimal_text))
    if not Fraction(1, 2) <= printed < 1:
        raise ValueError("binary80 parameter outside [.5,1)")
    recovered = Fraction(round(printed * 2**64), 2**64)
    print_error = abs(printed - recovered)
    if print_error > Fraction(1, 10**20):
        raise ValueError("21-digit print is too far from binary80 grid")
    return recovered, print_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("samples", "all-spans", "all-spans-receipt",
                 "contraction", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    samples = json.loads(args.samples.read_text())
    receipt = json.loads(args.all_spans_receipt.read_text())
    contraction = json.loads(args.contraction.read_text())
    if (samples["state"] != "SAMPLED_BINARY80_ANGLE_CELL_STABLE"
            or receipt["state"]
            != "ALL_ANALYTIC_SHAPED_SPANS_BITWISE_IDENTICAL"
            or receipt["raw_output_sha256"] != sha256(args.all_spans)
            or samples["h5_sha256"] != receipt["h5_sha256"]
            or contraction["state"]
            != "REAL_SAFEGUARDED_NEWTON_REACHES_ANGLE_CELL"
            or contraction["compiled_all_spans_sha256"]
            != sha256(args.all_spans)):
        raise ValueError("sample/power/contraction identities disagree")
    sample_by_member = {int(row["member"]): row
                        for row in samples["results"]}
    results = []
    for line in args.all_spans.read_text().splitlines():
        record = json.loads(line)
        member = int(record["member"])
        if (member not in sample_by_member
                or record["span"] != int(record["sample_count"]) - 1):
            continue
        power = [[Fraction.from_float(float.fromhex(value))
                  for value in record["power_hex"][axis]]
                 for axis in range(3)]
        angle_min = float.fromhex(record["angle_min_hex"])
        angle_max = float.fromhex(record["angle_max_hex"])
        width = angle_max - angle_min
        rows = []
        for sample in sample_by_member[member]["rows"]:
            query_x = Fraction.from_float(float.fromhex(
                sample["point_x_hex"]))
            loop_u, loop_print_error = recover_binary80(
                sample["loop_u_decimal"])
            best_u, best_print_error = recover_binary80(
                sample["best_u_decimal"])
            if loop_u != best_u:
                raise ValueError("distance ranking did not retain Newton u")
            coefficients = stationary(power, I.point(query_x))
            f = polynomial(coefficients, I.point(loop_u))
            if f.lo != f.hi:
                raise ValueError("point stationary polynomial not exact")
            slope_controls = controls_at(power, query_x)[
                "slope_bernstein"]
            m = min(slope_controls)
            if m <= 0:
                raise ValueError("stationary slope not positive")
            root_error = abs(f.lo) / m
            root_lo, root_hi = loop_u - root_error, loop_u + root_error
            angles = [angle_min + float(value) * width
                      for value in (root_lo, root_hi)]
            same_cell = all(value.hex() == sample["q_hex"]
                            for value in angles)
            rows.append({
                "point_x_hex": sample["point_x_hex"],
                "u_binary80_exact": str(loop_u),
                "q_hex": sample["q_hex"],
                "true_stationary_residual": float(f.lo),
                "true_root_parameter_error_upper": float(root_error),
                "print_error_upper_observed": float(max(
                    loop_print_error, best_print_error)),
                "root_bracket_same_angle_cell": same_cell,
            })
        results.append({
            "member": member, "sample_count": len(rows),
            "maximum_abs_true_stationary_residual": max(
                abs(row["true_stationary_residual"]) for row in rows),
            "maximum_true_root_parameter_error_upper": max(
                row["true_root_parameter_error_upper"] for row in rows),
            "maximum_print_error": max(row["print_error_upper_observed"]
                                       for row in rows),
            "same_angle_cell_count": sum(row["root_bracket_same_angle_cell"]
                                         for row in rows),
            "rows": rows,
        })
    results.sort(key=lambda row: row["member"])
    if [row["member"] for row in results] != [2, 3]:
        raise ValueError("expected two shaped last spans")
    achieved = all(row["sample_count"] == 39
                   and row["same_angle_cell_count"] == row["sample_count"]
                   for row in results)
    report = {
        "schema": "stellarcsg.sampled-binary80-true-stationarity/v1",
        "state": "SAMPLED_TRUE_STATIONARY_ROOTS_IN_ANGLE_CELL" if achieved
                 else "SAMPLED_STATIONARITY_UNDECIDED",
        "source_sha256": sha256(Path(__file__)),
        "stationary_helper_sha256": sha256(Path(stationary_model.__file__)),
        "control_helper_sha256": sha256(Path(contraction_model.__file__)),
        "samples_sha256": sha256(args.samples),
        "compiled_all_spans_sha256": sha256(args.all_spans),
        "compiled_all_spans_receipt_sha256": sha256(args.all_spans_receipt),
        "contraction_sha256": sha256(args.contraction),
        "results": results,
        "claim_boundary": "At each of 39 sampled rounded ray x values per shaped member, the diagnostic helper's 21-digit binary80 loop and selected u recover to the same 2^-64 grid point. Exact rational stored-power stationarity residuals and positive Bernstein slope bounds enclose a real stationary root in the same binary64 angle cell. This is sampled a posteriori evidence for the duplicated helper, not a continuous binary80 proof, BVH/frame certificate, earlier-root exclusion or native hit."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in results:
        print(row["member"], row["sample_count"],
              row["maximum_abs_true_stationary_residual"],
              row["maximum_true_root_parameter_error_upper"],
              row["same_angle_cell_count"])
    if not achieved:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
