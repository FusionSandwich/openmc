"""Replay compiled centerline box interval construction for analytic spans.

This is an independent Python binary64 transcription of the production
outward interval arithmetic. Bitwise box agreement complements the exact
real-curve containment audit; it is not an executable proof for every compiler
optimization or every imported surface.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_compiled_span_boxes import digest, rows


def outward(value: float, direction: float) -> float:
    if not math.isfinite(value):
        raise ValueError("nonfinite intermediate")
    result = math.nextafter(value, direction)
    if not math.isfinite(result):
        raise ValueError("nonfinite outward endpoint")
    return result


def product(coefficient: float, bounds: tuple[float, float]) -> tuple[float, float]:
    lower, upper = bounds
    low = coefficient * (lower if coefficient >= 0.0 else upper)
    high = coefficient * (upper if coefficient >= 0.0 else lower)
    return outward(low, -math.inf), outward(high, math.inf)


def power_range(power: list[float], u: tuple[float, float]) -> tuple[float, float]:
    value = power[3], power[3]
    for degree in (2, 1, 0):
        left = product(value[0], u)
        right = product(value[1], u)
        low = min(left[0], left[1], right[0], right[1])
        high = max(left[0], left[1], right[0], right[1])
        value = (outward(low + power[degree], -math.inf),
                 outward(high + power[degree], math.inf))
    return value


def box_for_row(row: dict) -> tuple[list[float], list[float]]:
    amin = float.fromhex(row["angle_min_hex"])
    amax = float.fromhex(row["angle_max_hex"])
    width = amax - amin
    if not (math.isfinite(width) and width > 0):
        raise ValueError("invalid span width")
    scale = 1.0 / width
    upper_u = outward(width * scale, math.inf)
    powers = [[float.fromhex(value) for value in axis]
              for axis in row["power_hex"]]
    lows = [math.inf] * 3
    highs = [-math.inf] * 3
    for tile in range(16):
        left = upper_u * float(tile) / 16.0
        right = upper_u * float(tile + 1) / 16.0
        u = (0.0 if tile == 0 else outward(left, -math.inf),
             upper_u if tile == 15 else outward(right, math.inf))
        for axis in range(3):
            lo, hi = power_range(powers[axis], u)
            lows[axis] = min(lows[axis], lo)
            highs[axis] = max(highs[axis], hi)
    return lows, highs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boxes", type=Path, required=True)
    parser.add_argument("--exact-receipt", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    exact = json.loads(args.exact_receipt.read_text())
    exact_auditor = Path(__file__).with_name("audit_compiled_span_boxes.py")
    if (exact.get("state") != "ALL_ANALYTIC_REAL_CENTERLINE_BOXES_ENCLOSE"
            or exact["sha256"]["boxes"] != digest(args.boxes)
            or exact["sha256"]["auditor"] != digest(exact_auditor)
            or exact["sha256"]["production_source"]
            != digest(args.production_source)):
        raise ValueError("exact real-curve receipt is mismatched")
    table = rows(args.boxes)
    expected = {(2, i) for i in range(256)} | {(3, i) for i in range(384)}
    if set(table) != expected:
        raise ValueError("unexpected span coverage")
    checks = 0
    for key in sorted(expected):
        row = table[key]
        lower, upper = box_for_row(row)
        for axis in range(3):
            if (lower[axis].hex() != float.fromhex(row["lower_hex"][axis]).hex()
                    or upper[axis].hex()
                    != float.fromhex(row["upper_hex"][axis]).hex()):
                raise ValueError(f"box-construction mismatch {key} axis {axis}")
            checks += 2
    result = {
        "schema": "stellarcsg.compiled-box-construction-replay/v1",
        "state": "ALL_ANALYTIC_CENTERLINE_BOX_ENDPOINTS_MATCH",
        "member_spans": {"2": 256, "3": 384},
        "compared_binary64_endpoints": checks,
        "sha256": {
            "auditor": digest(Path(__file__)),
            "exact_auditor": exact["sha256"]["auditor"],
            "boxes": digest(args.boxes),
            "exact_receipt": digest(args.exact_receipt),
            "production_source": digest(args.production_source),
        },
        "claim_boundary": "An independent Python binary64 replay of the source's sixteen-tile outward interval Horner construction exactly matches all 3,840 lower and upper endpoints of the compiled analytic centerline boxes. Together with the separate rational real-curve audit, this supports the box arithmetic for these members under IEEE binary64 round-to-nearest source order. It does not prove the optimized instructions, rounded angle-to-u mapping for every query, BVH traversal, nearest-center selection, earlier surface roots, or arbitrary imported coils."
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["state"], checks)


if __name__ == "__main__":
    main()
