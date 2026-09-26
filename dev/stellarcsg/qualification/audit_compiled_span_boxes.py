"""Audit all compiled analytic centerline boxes against exact cubic powers.

Each of sixteen local-u tiles is evaluated with rational interval Horner
arithmetic. This encloses the continuous stored-power polynomial, independent
of sampling. It does not model the C++ rounded Horner evaluation path.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rational(token: str) -> Fraction:
    return Fraction.from_float(float.fromhex(token))


def range_on_tile(power: list[Fraction], left: Fraction,
                  right: Fraction) -> tuple[Fraction, Fraction]:
    lo = hi = power[3]
    for order in (2, 1, 0):
        products = (lo * left, lo * right, hi * left, hi * right)
        lo, hi = min(products) + power[order], max(products) + power[order]
    return lo, hi


def rows(path: Path) -> dict[tuple[int, int], dict]:
    result = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = (row["member"], row["span"])
            if key in result:
                raise ValueError(f"duplicate row {key}")
            result[key] = row
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boxes", type=Path, required=True)
    parser.add_argument("--previous-powers", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--helper-executable", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    actual = rows(args.boxes)
    previous = rows(args.previous_powers)
    expected = {(2, i) for i in range(256)} | {(3, i) for i in range(384)}
    if set(actual) != expected or set(previous) != expected:
        raise ValueError("row coverage differs from 256+384 spans")
    minimum_slack = None
    tested_tiles = 0
    for key in sorted(expected):
        row, old = actual[key], previous[key]
        if (row["angle_min_hex"] != old["angle_min_hex"]
                or row["angle_max_hex"] != old["angle_max_hex"]
                or row["power_hex"] != old["power_hex"][:3]):
            raise ValueError(f"compiled-power identity mismatch at {key}")
        for axis in range(3):
            power = list(map(rational, row["power_hex"][axis]))
            box_lo = rational(row["lower_hex"][axis])
            box_hi = rational(row["upper_hex"][axis])
            if box_lo > box_hi:
                raise ValueError(f"inverted box at {key} axis {axis}")
            for tile in range(16):
                lo, hi = range_on_tile(
                    power, Fraction(tile, 16), Fraction(tile + 1, 16))
                if box_lo > lo or box_hi < hi:
                    raise ValueError(f"box misses real curve at {key} "
                                     f"axis {axis} tile {tile}")
                margin = min(lo - box_lo, box_hi - hi)
                minimum_slack = (margin if minimum_slack is None
                                 else min(minimum_slack, margin))
                tested_tiles += 1
    report = {
        "schema": "stellarcsg.compiled-span-box-exact/v1",
        "state": "ALL_ANALYTIC_REAL_CENTERLINE_BOXES_ENCLOSE",
        "member_spans": {"2": 256, "3": 384},
        "axes_per_span": 3,
        "tiles_per_axis": 16,
        "exact_interval_tests": tested_tiles,
        "minimum_exact_margin_cm": float(minimum_slack),
        "sha256": {
            "auditor": digest(Path(__file__)),
            "boxes": digest(args.boxes),
            "previous_powers": digest(args.previous_powers),
            "helper_source": digest(args.helper_source),
            "production_source": digest(args.production_source),
            "helper_executable": digest(args.helper_executable),
            "standalone_library": digest(args.library),
            "analytic_h5": digest(args.h5),
        },
        "claim_boundary": "All 640 current compiled analytic span boxes enclose the continuous real cubic represented by their bitwise-matched stored powers, by exact rational interval Horner on 16 local-u tiles. This does not independently enclose rounded C++ frame evaluation, validate BVH node traversal, certify nearest-center selection, prove earlier surface roots absent, or generalize to arbitrary imported coils."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"], tested_tiles, float(minimum_slack))


if __name__ == "__main__":
    main()
