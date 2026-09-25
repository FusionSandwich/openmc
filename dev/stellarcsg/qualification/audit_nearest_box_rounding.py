"""Show why ordinary binary64 squared distances are unsafe pruning bounds."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def outward(value: float, upward: bool) -> float:
    if not math.isfinite(value):
        return math.inf if upward else float.fromhex("0x1.fffffffffffffp+1023")
    if value <= 0.0:
        return 0.0
    return math.nextafter(value, math.inf if upward else -math.inf)


def squared_bound(first: float, second: float, upward: bool) -> float:
    gap = outward(abs(first - second), upward)
    square = outward(gap * gap, upward)
    return outward(outward(square, upward), upward)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    cases = [
        ("box_lower_rounds_above_true_gap", -3.4116076015446017,
         -2.1120778893504912, False),
        ("candidate_distance_rounds_below_true", -8.541830026153008,
         -9.683717401878845, True),
    ]
    rows = []
    for name, first, second, upward in cases:
        exact = (Fraction.from_float(first) - Fraction.from_float(second)) ** 2
        ordinary = (first - second) ** 2
        bound = squared_bound(first, second, upward)
        valid = (Fraction.from_float(bound) >= exact if upward
                 else Fraction.from_float(bound) <= exact)
        ordinary_wrong_way = (Fraction.from_float(ordinary) < exact if upward
                              else Fraction.from_float(ordinary) > exact)
        if not valid or not ordinary_wrong_way:
            raise AssertionError(f"rounding witness did not reproduce: {name}")
        rows.append({"name": name, "first": first, "second": second,
                     "ordinary_squared": ordinary, "outward_squared": bound,
                     "ordinary_minus_exact": float(Fraction.from_float(ordinary)
                                                   - exact),
                     "bound_minus_exact": float(Fraction.from_float(bound)
                                                - exact),
                     "ordinary_wrong_way": ordinary_wrong_way,
                     "outward_bound_valid": valid})
    report = {
        "schema": "stellarcsg.nearest-box-rounding-witness/v1",
        "state": "BINARY64_ROUNDING_DIRECTION_WITNESSES",
        "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rows": rows,
        "claim_boundary": "Exact rational comparisons for two one-axis binary64 arithmetic witnesses. They demonstrate that ordinary rounded squared distances can overstate a box lower bound or understate a candidate upper bound. They do not prove every C++ bounding expression or that an earlier real coil query was misclassified.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"state": report["state"], "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
