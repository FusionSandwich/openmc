"""Check exact rational containment of the compiled centerline Horner boxes."""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

from audit_compiled_span_boxes import digest, rows


CONSTRUCTION_RECEIPT_SHA256 = "ee4224416b14f8c26377a03e049d0242f3e4f6f9f09941b57ca4c399ad2a2813"


def rational(value: float) -> Fraction:
    if not math.isfinite(value):
        raise ValueError("nonfinite floating endpoint")
    return Fraction.from_float(value)


def outward(value: float, direction: float) -> float:
    if not math.isfinite(value):
        raise ValueError("nonfinite interval operation")
    result = math.nextafter(value, direction)
    if not math.isfinite(result):
        raise ValueError("nonfinite outward interval endpoint")
    return result


def multiply_bound(coefficient: float, u: tuple[float, float]) -> tuple[float, float]:
    selected_low = u[0] if coefficient >= 0.0 else u[1]
    selected_high = u[1] if coefficient >= 0.0 else u[0]
    low = outward(coefficient * selected_low, -math.inf)
    high = outward(coefficient * selected_high, math.inf)
    if (rational(low) > rational(coefficient) * rational(selected_low)
            or rational(high) < rational(coefficient) * rational(selected_high)):
        raise ValueError("outward product misses exact binary64-operand product")
    return low, high


def horner_bound(power: list[float], u: tuple[float, float]) -> tuple[float, float]:
    value = power[3], power[3]
    for degree in (2, 1, 0):
        left = multiply_bound(value[0], u)
        right = multiply_bound(value[1], u)
        low = min(*left, *right)
        high = max(*left, *right)
        new_low = outward(low + power[degree], -math.inf)
        new_high = outward(high + power[degree], math.inf)
        if (rational(new_low) > rational(low) + rational(power[degree])
                or rational(new_high) < rational(high)
                + rational(power[degree])):
            raise ValueError("outward sum misses exact binary64-operand sum")
        value = new_low, new_high
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boxes", type=Path, required=True)
    parser.add_argument("--construction-receipt", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    if digest(args.construction_receipt) != CONSTRUCTION_RECEIPT_SHA256:
        raise ValueError("compiled construction receipt differs")
    construction = json.loads(args.construction_receipt.read_text())
    if (construction["schema"] != "stellarcsg.compiled-box-construction-replay/v1"
            or construction["state"]
            != "ALL_ANALYTIC_CENTERLINE_BOX_ENDPOINTS_MATCH"
            or construction["compared_binary64_endpoints"] != 3840
            or construction["sha256"]["boxes"] != digest(args.boxes)
            or construction["sha256"]["production_source"]
            != digest(args.production_source)):
        raise ValueError("compiled box construction lineage differs")
    table = rows(args.boxes)
    expected = {(2, i) for i in range(256)} | {(3, i) for i in range(384)}
    if set(table) != expected:
        raise ValueError("analytic span coverage differs")
    tile_checks = 0
    axis_checks = 0
    operation_bounds = 0
    for key in sorted(expected):
        row = table[key]
        amin = float.fromhex(row["angle_min_hex"])
        amax = float.fromhex(row["angle_max_hex"])
        width = amax - amin
        if not (math.isfinite(width) and width > 0):
            raise ValueError(f"nonpositive span width {key}")
        scale = 1.0 / width
        upper_u = outward(width * scale, math.inf)
        if not (upper_u >= width * scale > 0.0):
            raise ValueError(f"rounded endpoint mapping differs {key}")
        # evaluate_in_span maps a selected best_u in [0, 1] back to q using
        # this source-order expression before frame_in_span maps q to local u.
        q_high = amin + 1.0 * width
        mapped_high = (q_high - amin) * scale
        if q_high > amax or mapped_high > upper_u:
            raise ValueError(f"selected-angle mapping escapes box {key}")
        powers = [[float.fromhex(value) for value in axis]
                  for axis in row["power_hex"]]
        lower = [math.inf] * 3
        upper = [-math.inf] * 3
        previous_high = None
        for tile in range(16):
            left = upper_u * float(tile) / 16.0
            right = upper_u * float(tile + 1) / 16.0
            local_u = (0.0 if tile == 0 else outward(left, -math.inf),
                       upper_u if tile == 15 else outward(right, math.inf))
            if (not 0.0 <= local_u[0] <= local_u[1]
                    or previous_high is not None
                    and previous_high < local_u[0]):
                raise ValueError(f"local-u tile gap {key} tile {tile}")
            previous_high = local_u[1]
            for axis in range(3):
                lo, hi = horner_bound(powers[axis], local_u)
                lower[axis] = min(lower[axis], lo)
                upper[axis] = max(upper[axis], hi)
                axis_checks += 1
                operation_bounds += 18
            tile_checks += 1
        if previous_high != upper_u:
            raise ValueError(f"tile cover misses upper endpoint {key}")
        for axis in range(3):
            if (lower[axis].hex()
                    != float.fromhex(row["lower_hex"][axis]).hex()
                    or upper[axis].hex()
                    != float.fromhex(row["upper_hex"][axis]).hex()):
                raise ValueError(f"compiled box mismatch {key} axis {axis}")
    receipt = {
        "schema": "stellarcsg.compiled-horner-enclosure/v1",
        "state": "ALL_ANALYTIC_ROUNDED_HORNER_BOXES_ENCLOSE",
        "member_spans": {"2": 256, "3": 384},
        "covered_local_u_tiles": tile_checks,
        "selected_angle_endpoint_checks": len(expected),
        "axis_tile_checks": axis_checks,
        "exact_rational_product_and_sum_bound_checks": operation_bounds,
        "hashes": {"auditor": digest(Path(__file__)),
                   "boxes": digest(args.boxes),
                   "construction_receipt": digest(args.construction_receipt),
                   "production_source": digest(args.production_source)},
        "claim_boundary": "Every outward binary64 interval product and sum in the 16-tile centerline Horner replay encloses the corresponding exact operation on its binary64 operands, with no local-u tile gaps. Each source-order selected-angle endpoint maps inside the local-u cover; monotonic correctly rounded arithmetic covers intermediate selected parameters in [0,1]. The resulting 3,840 box endpoints match the compiled dump for two analytic members. Under correctly rounded binary64 operations and the source's evaluation order, these boxes enclose the rounded Horner center. This does not independently prove optimized instruction order, arbitrary imported payloads, BVH traversal, nearest-root selection, frame normalization, or transport performance.",
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"], axis_checks, operation_bounds)


if __name__ == "__main__":
    main()
