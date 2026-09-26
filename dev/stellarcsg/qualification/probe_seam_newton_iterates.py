"""Trace exact interval Newton iterates for analytic seam stationary roots.

This follows the branch structure of the compiled safeguarded loop using
exact rational intervals. It intentionally omits long-double rounding and
is exploratory until a separate operation-error enclosure is attached.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class I:
    lo: Fraction
    hi: Fraction

    @classmethod
    def point(cls, value: Fraction | int) -> "I":
        return cls(Fraction(value), Fraction(value))

    def __add__(self, other: "I") -> "I":
        return I(self.lo + other.lo, self.hi + other.hi)

    def __neg__(self) -> "I":
        return I(-self.hi, -self.lo)

    def __sub__(self, other: "I") -> "I":
        return self + -other

    def __mul__(self, other: "I") -> "I":
        values = (self.lo * other.lo, self.lo * other.hi,
                  self.hi * other.lo, self.hi * other.hi)
        return I(min(values), max(values))

    def __truediv__(self, other: "I") -> "I":
        if other.lo <= 0 <= other.hi:
            raise ZeroDivisionError("interval denominator contains zero")
        return self * I(min(1 / other.lo, 1 / other.hi),
                        max(1 / other.lo, 1 / other.hi))

    def pair(self) -> list[float]:
        return [float(self.lo), float(self.hi)]


def polynomial(coefficients: list[I], u: I) -> I:
    result = coefficients[-1]
    for coefficient in reversed(coefficients[:-1]):
        result = result * u + coefficient
    return result


def stationary(power: list[list[Fraction]], query_x: I) -> list[I]:
    query = [query_x, I.point(0), I.point(0)]
    coefficients = [I.point(0) for _ in range(6)]
    for axis in range(3):
        center = [I.point(value) for value in power[axis]]
        offset = center.copy()
        offset[0] = offset[0] - query[axis]
        for i in range(4):
            for j in range(3):
                coefficients[i + j] = coefficients[i + j] + (
                    offset[i] * I.point(j + 1) * center[j + 1])
    return coefficients


def trace(coefficients: list[I], cap: int) -> list[dict]:
    slope = [coefficients[k] * I.point(k) for k in range(1, 6)]
    left, right, u = I.point(0), I.point(1), I.point(Fraction(1, 2))
    rows = []
    for index in range(cap):
        value = polynomial(coefficients, u)
        if value.lo == value.hi == 0:
            rows.append({"iteration": index, "state": "EXACT_ZERO",
                         "u": u.pair()})
            break
        if value.hi < 0:
            side = "left"
            left = u
        elif value.lo > 0:
            side = "right"
            right = u
        else:
            rows.append({"iteration": index, "state": "UNDECIDED_SIGN",
                         "u": u.pair(), "value": value.pair()})
            break
        derivative = polynomial(slope, u)
        if derivative.lo <= 0:
            rows.append({"iteration": index, "state": "UNDECIDED_SLOPE",
                         "u": u.pair(), "derivative": derivative.pair()})
            break
        newton = u - value / derivative
        if left.hi < newton.lo and newton.hi < right.lo:
            method = "newton"
            next_u = newton
        elif newton.hi <= left.lo or newton.lo >= right.hi:
            method = "midpoint"
            next_u = (left + right) * I.point(Fraction(1, 2))
        else:
            rows.append({"iteration": index, "state": "UNDECIDED_GUARD",
                         "u": u.pair(), "newton": newton.pair(),
                         "left": left.pair(), "right": right.pair()})
            break
        rows.append({"iteration": index, "state": "STEP", "side": side,
                     "method": method, "u": u.pair(),
                     "value": value.pair(),
                     "derivative": derivative.pair(),
                     "next": next_u.pair()})
        u = next_u
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stationary", type=Path, required=True)
    parser.add_argument("--all-spans", type=Path, required=True)
    parser.add_argument("--all-spans-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--point-iterations", type=int, default=6)
    parser.add_argument("--partitions", type=int, default=16)
    args = parser.parse_args()
    if (args.output.exists() or not 1 <= args.iterations <= 80
            or not 1 <= args.point_iterations <= 6
            or not 1 <= args.partitions <= 4096):
        parser.error("output must be new; point cap 6, partitions <=4096")
    stationary_receipt = json.loads(args.stationary.read_text())
    all_spans_receipt = json.loads(args.all_spans_receipt.read_text())
    if (stationary_receipt["state"]
            != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED"
            or all_spans_receipt["state"]
            != "ALL_ANALYTIC_SHAPED_SPANS_BITWISE_IDENTICAL"
            or all_spans_receipt["raw_output_sha256"]
            != sha256(args.all_spans)
            or all_spans_receipt["h5_sha256"]
            != stationary_receipt["h5_sha256"]):
        raise ValueError("stationary and compiled span identities disagree")
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
        query_x = I(Fraction.from_float(550.0 - thi),
                    Fraction.from_float(550.0 - tlo))
        rows = trace(stationary(power, query_x), args.iterations)
        partition_states: dict[str, int] = {}
        partition_methods: dict[str, int] = {}
        partition_undecided = []
        width = (query_x.hi - query_x.lo) / args.partitions
        for index in range(args.partitions):
            cell = I(query_x.lo + width * index,
                     query_x.lo + width * (index + 1))
            cell_rows = trace(stationary(power, cell), min(args.iterations, 6))
            state = cell_rows[-1]["state"]
            partition_states[state] = partition_states.get(state, 0) + 1
            for step in cell_rows:
                method = step.get("method")
                if method:
                    partition_methods[method] = partition_methods.get(method, 0) + 1
            if state.startswith("UNDECIDED"):
                partition_undecided.append({"index": index,
                                            "query_x": cell.pair(),
                                            "iteration": cell_rows[-1]["iteration"],
                                            "state": state})
        point_traces = []
        for label, point_x in (("lower_x", query_x.lo),
                               ("mid_x", (query_x.lo + query_x.hi) / 2),
                               ("upper_x", query_x.hi)):
            point_rows = trace(stationary(power, I.point(point_x)),
                               args.point_iterations)
            point_traces.append({
                "label": label, "query_x_cm": float(point_x),
                "step_count": sum(row["state"] == "STEP"
                                  for row in point_rows),
                "midpoint_steps": sum(row.get("method") == "midpoint"
                                      for row in point_rows),
                "newton_steps": sum(row.get("method") == "newton"
                                    for row in point_rows),
                "terminal_state": point_rows[-1]["state"],
                "last_three": point_rows[-3:],
            })
        results.append({"member": member, "span": record["span"],
                        "rounded_query_x": query_x.pair(), "iterates": rows,
                        "partition_summary": {
                            "count": args.partitions,
                            "terminal_states": partition_states,
                            "methods": partition_methods,
                            "undecided_preview": partition_undecided[:8]},
                        "point_traces": point_traces})
    results.sort(key=lambda row: row["member"])
    if [row["member"] for row in results] != [2, 3]:
        raise ValueError("expected two shaped seam spans")
    report = {"schema": "stellarcsg.seam-exact-newton-interval-probe/v1",
              "state": "EXPLORATORY_REAL_ARITHMETIC_ONLY",
              "source_sha256": sha256(Path(__file__)),
              "stationary_sha256": sha256(args.stationary),
              "compiled_all_spans_sha256": sha256(args.all_spans),
              "compiled_all_spans_receipt_sha256": sha256(
                  args.all_spans_receipt),
              "interval_iteration_cap": args.iterations,
              "point_iteration_cap": args.point_iterations,
              "partitions_per_member": args.partitions,
              "results": results,
              "claim_boundary": "Exact rational interval trace of the source safeguarded Newton branch over the full rounded-query strip. A trace step is emitted only when sign and guard have uniform outcomes. No long-double error or actual compiled iteration is enclosed, and no native hit is admitted."}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for row in results:
        print(row["member"], [(step["state"], step.get("method"),
                              step.get("next", step["u"]))
                             for step in row["iterates"]])
        print("points", [(point["label"], point["step_count"],
                          point["midpoint_steps"], point["newton_steps"],
                          point["terminal_state"])
                         for point in row["point_traces"]])
        print("partitions", row["partition_summary"])


if __name__ == "__main__":
    main()
