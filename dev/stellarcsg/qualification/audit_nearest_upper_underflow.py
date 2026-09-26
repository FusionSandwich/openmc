"""Reproduce the exact-distance upper-bound underflow counterexample.

Uses exact rational binary64 inputs. The old zero special case yielded zero
for a positive squared distance; the repaired expression widens zero too.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def widened(value: float, *, old: bool) -> float:
    if not math.isfinite(value):
        return math.inf
    if old and value <= 0.0:
        return 0.0
    return math.nextafter(max(0.0, value), math.inf)


def upper(point: tuple[float, float, float], center: tuple[float, float, float],
          *, old: bool) -> float:
    differences = [widened(abs(a - b), old=old)
                   for a, b in zip(point, center)]
    squares = [widened(value * value, old=old) for value in differences]
    return widened(widened(squares[0] + squares[1], old=old)
                   + squares[2], old=old)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    minimum_subnormal = math.ldexp(1.0, -1074)
    point = (minimum_subnormal, 0.0, 0.0)
    center = (0.0, 0.0, 0.0)
    exact = Fraction.from_float(minimum_subnormal) ** 2
    old = upper(point, center, old=True)
    repaired = upper(point, center, old=False)
    if not (old == 0.0 and exact > 0
            and Fraction.from_float(repaired) >= exact):
        raise ValueError("underflow witness did not reproduce")
    report = {
        "schema": "stellarcsg.nearest-upper-underflow/v1",
        "state": "EXACT_UPPER_UNDERFLOW_WITNESS_REPAIRED",
        "source_sha256": sha256(Path(__file__)),
        "production_source_sha256": sha256(args.production_source),
        "point_hex": [value.hex() for value in point],
        "center_hex": [value.hex() for value in center],
        "exact_squared_distance": "2^-2148",
        "old_upper_hex": old.hex(),
        "repaired_upper_hex": repaired.hex(),
        "repaired_is_exact_upper": Fraction.from_float(repaired) >= exact,
        "claim_boundary": "Exact rational comparison for the smallest-positive-binary64 one-axis gap. The old Python reproduction of point_distance_squared_upper returned zero, below the positive exact square. Widening zero in every nonnegative step returns a strict upper. This checks the changed arithmetic case, not all compiler paths, BVH boxes, earlier roots or native transport."
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["state"], old.hex(), repaired.hex())


if __name__ == "__main__":
    main()
