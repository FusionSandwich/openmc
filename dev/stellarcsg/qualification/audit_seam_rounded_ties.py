"""Compare compiled seam samples with first-span rounded distance ties.

This is a finite sample diagnostic. It does not certify span selection over
the continuous seam strip or the C++ BVH traversal order.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_d2(point_x: float, center: list[float]) -> float:
    # Matches vector.hpp dot(point - center, point - center) operation order.
    dx = point_x - center[0]
    dy = -center[1]
    dz = -center[2]
    return dx * dx + dy * dy + dz * dz


def exact_d2(point_x: float, center: list[Fraction]) -> Fraction:
    dx = Fraction.from_float(point_x) - center[0]
    return dx * dx + center[1] * center[1] + center[2] * center[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--all-spans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    samples = json.loads(args.samples.read_text())
    spans = {}
    for line in args.all_spans.read_text().splitlines():
        record = json.loads(line)
        member = int(record["member"])
        span = int(record["span"])
        if span in (0, int(record["sample_count"]) - 1):
            spans[(member, span)] = record
    results = []
    for group in samples["results"]:
        member = int(group["member"])
        first = spans[(member, 0)]
        last = spans[(member, int(group["span"]))]
        first_power = [[Fraction.from_float(float.fromhex(value))
                        for value in first["power_hex"][axis]]
                       for axis in range(3)]
        last_power = [[Fraction.from_float(float.fromhex(value))
                       for value in last["power_hex"][axis]]
                      for axis in range(3)]
        first_center = [axis[0] for axis in first_power]
        last_endpoint = [sum(axis) for axis in last_power]
        rows = []
        for sample in group["samples"]:
            point_x = float(sample["point_x_cm"])
            compiled_center = [float(value) for value in sample["center_cm"]]
            first_rounded = [float(value) for value in first_center]
            first_native = native_d2(point_x, first_rounded)
            selected_native = native_d2(point_x, compiled_center)
            delta_exact = exact_d2(point_x, last_endpoint) - exact_d2(
                point_x, first_center)
            rows.append({
                "point_x_hex": point_x.hex(),
                "selected_center_hex": [x.hex() for x in compiled_center],
                "first_center_hex": [x.hex() for x in first_rounded],
                "first_native_d2_hex": first_native.hex(),
                "selected_native_d2_hex": selected_native.hex(),
                "rounded_distance_tie": first_native == selected_native,
                "exact_last_endpoint_minus_first_d2_cm2": float(delta_exact),
                "exact_last_endpoint_strictly_nearer": delta_exact < 0,
            })
        results.append({"member": member, "sample_count": len(rows),
                        "rounded_tie_count": sum(row["rounded_distance_tie"]
                                                 for row in rows),
                        "exact_last_endpoint_nearer_count": sum(
                            row["exact_last_endpoint_strictly_nearer"]
                            for row in rows),
                        "samples": rows})
    receipt = {
        "schema": "stellarcsg.seam-rounded-distance-ties/v1",
        "state": "SAMPLED_ROUNDED_DISTANCE_TIES" if all(
            row["rounded_tie_count"] == row["sample_count"] and
            row["exact_last_endpoint_nearer_count"] == row["sample_count"]
            for row in results) else "MIXED_SAMPLES",
        "source_sha256": sha256(Path(__file__)),
        "samples_sha256": sha256(args.samples),
        "compiled_all_spans_sha256": sha256(args.all_spans),
        "results": results,
        "claim_boundary": "At the saved compiled sample points, the native-style binary64 squared distances from the first-span endpoint center and the compiled selected center tie, while exact rational stored-power last-endpoint distance is strictly smaller. The sampled compiled center and first-span power are independently sourced; no untested angle, continuous interval, or BVH selection is certified."
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    for row in results:
        print(row["member"], row["rounded_tie_count"],
              row["exact_last_endpoint_nearer_count"],
              row["sample_count"])


if __name__ == "__main__":
    main()
