"""Exact-rational root isolation for retained binary64 circular-tube controls.

This offline oracle uses integer/Fraction Sturm arithmetic, never production
BVHs, local coordinates, finite-surface evaluation, or NumPy root trimming.
The authoritative mathematical object is the cardinal cubic of the EXACT
binary64 input controls and the line through the EXACT binary64 ray vectors.
Production coefficient conversion/evaluation roundoff is not silently adopted.
Radius is constant and circular; this oracle does not validate elliptic coils,
self-intersection, or transport admissibility. Root-completeness certificates
cover only queries whose every span and exceptional algebraic case resolved.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
from functools import reduce
import hashlib
import json
import math
from pathlib import Path
import time


def trim(p):
    p = list(p)
    while len(p) > 1 and not p[-1]:
        p.pop()
    return p


def primitive(p):
    """Positive rescaling only; preserve signs for a Sturm sequence."""
    p = trim(p)
    denominator = reduce(math.lcm, (x.denominator for x in p), 1)
    integers = [x.numerator*(denominator//x.denominator) for x in p]
    common = reduce(math.gcd, integers, 0)
    return [F(x//common) for x in integers] if common else [F(0)]


def add(a, b):
    p = [F(0)]*max(len(a), len(b))
    for i, x in enumerate(a):
        p[i] += x
    for i, x in enumerate(b):
        p[i] += x
    return trim(p)


def scale(a, s):
    return trim([x*s for x in a])


def mul(a, b):
    p = [F(0)]*(len(a)+len(b)-1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            p[i+j] += x*y
    return trim(p)


def derivative(p):
    return [i*p[i] for i in range(1, len(p))] or [F(0)]


def value(p, x):
    v = F(0)
    for coefficient in reversed(p):
        v = v*x+coefficient
    return v


def divide(a, b):
    a, b = trim(a), trim(b)
    if b == [0]:
        raise ZeroDivisionError("zero polynomial")
    q = [F(0)]*max(1, len(a)-len(b)+1)
    while a != [0] and len(a) >= len(b):
        i = len(a)-len(b)
        coefficient = a[-1]/b[-1]
        q[i] += coefficient
        for j, x in enumerate(b):
            a[i+j] -= coefficient*x
        a = trim(a)
    return trim(q), a


def gcd(a, b):
    a, b = primitive(a), primitive(b)
    while b != [0]:
        _, remainder = divide(a, b)
        a, b = b, primitive(remainder)
    return scale(a, 1/a[-1]) if a != [0] else a


def squarefree(p):
    if len(p) <= 1:
        return p
    q, remainder = divide(p, gcd(p, derivative(p)))
    assert remainder == [0]
    return primitive(q)


def remove_factor(p, factor):
    if len(factor) <= 1:
        return p
    while True:
        common = gcd(p, factor)
        if len(common) <= 1:
            return p
        p, remainder = divide(p, common)
        assert remainder == [0]


def sturm(p):
    sequence = [primitive(p), primitive(derivative(p))]
    while sequence[-1] != [0]:
        _, remainder = divide(sequence[-2], sequence[-1])
        if remainder == [0]:
            break
        sequence.append(primitive(scale(remainder, -1)))
    return sequence


def variation(sequence, x):
    signs = [1 if y > 0 else -1 for p in sequence if (y := value(p, x))]
    return sum(a != b for a, b in zip(signs, signs[1:]))


def isolate(p, bits=60, max_nodes=20000):
    """All distinct real roots in [0,1]; exact count, rational enclosures."""
    p = squarefree(p)
    if p == [0]:
        raise ArithmeticError("identically_zero_isolation_polynomial")
    intervals = []
    for endpoint in (F(0), F(1)):
        if len(p) > 1 and not value(p, endpoint):
            intervals.append((endpoint, endpoint))
            p, remainder = divide(p, [-endpoint, F(1)])
            assert remainder == [0]
    if len(p) <= 1:
        return intervals
    sequence = sturm(p)
    pending = [(F(0), F(1), variation(sequence, F(0))-variation(sequence, F(1)))]
    target = F(1, 1 << bits)
    nodes = 0
    while pending:
        lo, hi, count = pending.pop()
        if not count:
            continue
        nodes += 1
        if nodes > max_nodes:
            raise ArithmeticError("exact_sturm_node_budget_exhausted")
        if count == 1 and hi-lo <= target:
            intervals.append((lo, hi))
            continue
        denominator = 2
        split = (lo+hi)/2
        while not value(p, split):
            denominator += 1
            split = lo+(hi-lo)/denominator
        left_count = variation(sequence, lo)-variation(sequence, split)
        pending.append((split, hi, count-left_count))
        pending.append((lo, split, left_count))
    return sorted(intervals)


def interval_add(a, b):
    return a[0]+b[0], a[1]+b[1]


def interval_mul(a, b):
    candidates = [x*y for x in a for y in b]
    return min(candidates), max(candidates)


def interval_scale(a, s):
    return interval_mul(a, (s, s))


def interval_value(p, x):
    result = (F(0), F(0))
    for coefficient in reversed(p):
        result = interval_add(interval_mul(result, x), (coefficient, coefficient))
    return result


def interval_divide(a, b):
    if b[0] <= 0 <= b[1]:
        raise ArithmeticError("denominator_not_excluded_from_zero")
    return interval_mul(a, (1/b[1], 1/b[0]))


def sqrt_enclosure(x, bits=100):
    if x < 0:
        raise ArithmeticError("negative_square_root")
    denominator = 1 << bits
    lower = math.isqrt((x.numerator << (2*bits))//x.denominator)
    return F(lower, denominator), F(lower+1, denominator)


def dot(a, b):
    result = [F(0)]
    for x, y in zip(a, b):
        result = add(result, mul(x, y))
    return result


def spans(controls):
    # Exact cardinal basis, no coefficients eliminated using a tolerance.
    basis = [[F(1, 6), F(-1, 2), F(1, 2), F(-1, 6)],
             [F(2, 3), F(0), F(-1), F(1, 2)],
             [F(1, 6), F(1, 2), F(1, 2), F(-1, 2)],
             [F(0), F(0), F(0), F(1, 6)]]
    result = []
    for i in range(len(controls)):
        result.append([
            reduce(add, (scale(basis[a], F(controls[(i+a-1) % len(controls)][axis]))
                         for a in range(4)), [F(0)]) for axis in range(3)])
    return result


def span_bounds(c, radius):
    # Exact power-to-Bernstein conversion, convex-hull plus circular radius.
    result = []
    for p in c:
        p = p+[F(0)]*(4-len(p))
        bezier = [p[0], p[0]+p[1]/3, p[0]+2*p[1]/3+p[2]/3, sum(p)]
        result.append((min(bezier)-radius, max(bezier)+radius))
    return result


def intersects_bounds(bounds, origin, direction):
    """Exact rational slab exclusion; parallel means exactly zero."""
    enter, leave = None, None
    for box, o, d in zip(bounds, origin, direction):
        if not d:
            if not box[0] <= o <= box[1]:
                return False
            continue
        a, b = sorted(((box[0]-o)/d, (box[1]-o)/d))
        enter = a if enter is None else max(enter, a)
        leave = b if leave is None else min(leave, b)
        if enter > leave:
            return False
    return leave is None or leave >= 0


def exact_query(coil, radius, origin, direction):
    origin = list(map(F, origin))
    direction = list(map(F, direction))
    q = sum(d*d for d in direction)
    if not q:
        raise ValueError("zero ray direction")
    q_sqrt = sqrt_enclosure(q)
    candidates, diagnostics = [], {"excluded_spans": 0, "generic_roots": 0,
                                  "degenerate_roots": 0, "zero_start_factors": 0}
    for span_id, c in enumerate(coil):
        if not intersects_bounds(span_bounds(c, radius), origin, direction):
            diagnostics["excluded_spans"] += 1
            continue
        cp = [derivative(p) for p in c]
        offset = [add([o], scale(p, -1)) for o, p in zip(origin, c)]
        a = dot([[d] for d in direction], cp)
        b = dot(offset, cp)
        d = dot([[x] for x in direction], offset)
        e = add(dot(offset, offset), [-radius*radius])
        resultant = add(add(scale(mul(b, b), q), scale(mul(mul(a, b), d), -2)),
                        mul(mul(a, a), e))
        exceptional = gcd(a, b)
        if a == [0] and b == [0]:
            raise ArithmeticError(f"span_{span_id}_identically_degenerate")
        generic = [F(1)] if resultant == [0] else remove_factor(resultant, exceptional)
        # At a generic root with B=0, A!=0 implies E=0 and lambda=0.
        zero_factor = gcd(generic, b)
        if len(zero_factor) > 1:
            diagnostics["zero_start_factors"] += len(zero_factor)-1
            generic = remove_factor(generic, zero_factor)
        if a == [0]:
            generic = [F(1)]
        for bits in (60, 100, 160, 240):
            pending_generic = []
            resolved = True
            for u in isolate(generic, bits):
                av, bv = interval_value(a, u), interval_value(b, u)
                try:
                    lam = interval_divide(interval_scale(bv, -1), av)
                except ArithmeticError:
                    resolved = False
                    break
                if lam[1] <= 0:
                    continue
                t = interval_mul(lam, q_sqrt)
                if lam[0] <= 0 or t[1]-t[0] > F(1, 10**13):
                    resolved = False
                    break
                pending_generic.append((t, span_id, u, "generic"))
            if resolved:
                candidates.extend(pending_generic)
                diagnostics["generic_roots"] += len(pending_generic)
                break
        else:
            raise ArithmeticError(f"span_{span_id}_generic_recovery_unresolved")
        if len(exceptional) <= 1:
            continue
        discriminant = add(mul(d, d), scale(e, -q))
        tangent_factor = gcd(exceptional, discriminant)
        regular_exceptional = remove_factor(exceptional, tangent_factor)
        # Exact discriminant-zero root: repeated ray intersection, lambda=-D/Q.
        for u in isolate(tangent_factor, 100):
            lam = interval_scale(interval_value(d, u), -1/q)
            if lam[1] <= 0:
                continue
            t = interval_mul(lam, q_sqrt)
            if lam[0] <= 0 or t[1]-t[0] > F(1, 10**13):
                raise ArithmeticError(f"span_{span_id}_degenerate_tangent_recovery")
            candidates.append((t, span_id, u, "exact_degenerate_tangent"))
            diagnostics["degenerate_roots"] += 1
        for bits in (60, 100, 160, 240):
            pending_exceptional, resolved = [], True
            for u in isolate(regular_exceptional, bits):
                disc = interval_value(discriminant, u)
                if disc[1] < 0:
                    continue
                if disc[0] <= 0:
                    resolved = False
                    break
                root_disc = (sqrt_enclosure(disc[0])[0],
                             sqrt_enclosure(disc[1])[1])
                dv = interval_value(d, u)
                for sign in (-1, 1):
                    lam = interval_scale(interval_add(interval_scale(dv, -1),
                                                     interval_scale(root_disc, sign)), 1/q)
                    if lam[1] <= 0:
                        continue
                    t = interval_mul(lam, q_sqrt)
                    if lam[0] <= 0 or t[1]-t[0] > F(1, 10**13):
                        resolved = False
                        break
                    pending_exceptional.append((t, span_id, u, "degenerate"))
            if resolved:
                candidates.extend(pending_exceptional)
                diagnostics["degenerate_roots"] += len(pending_exceptional)
                break
        else:
            raise ArithmeticError(f"span_{span_id}_degenerate_recovery_unresolved")
    candidates.sort(key=lambda candidate: candidate[0][0])
    # Taking minima of all lower and upper bounds encloses the nearest root
    # even when duplicate seam-root intervals overlap.
    nearest = ((min(c[0][0] for c in candidates), min(c[0][1] for c in candidates))
               if candidates else None)
    return nearest, candidates, diagnostics


def float_interval(interval):
    return [math.nextafter(float(interval[0]), -math.inf),
            math.nextafter(float(interval[1]), math.inf)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--shape", type=int)
    parser.add_argument("--index", type=int)
    parser.add_argument("--rigid", action="store_true",
                        help="Reconstruct fixture binary64 rotate/translate operations")
    parser.add_argument("--transform-dump", type=Path,
                        help="C++ hexfloat payload dump; require bitwise agreement when supplied")
    args = parser.parse_args()
    raw = args.capture.read_bytes()
    old = json.loads(args.previous.read_text())
    blocked = {(x["shape"], x["index"]): x for x in old["results"]
               if x["oracle_state"] == "BLOCKED"}
    records = [json.loads(line) for line in raw.splitlines()]
    def rotate(p):
        return [0.6*p[0]-0.8*p[2], p[1], 0.8*p[0]+0.6*p[2]]

    def placed(p):
        return [a+b for a, b in zip(rotate(p), [11., -7., 3.])]

    verified_transform_values = 0
    if args.transform_dump:
        controls_by_shape = {x["shape"]: x["controls"] for x in records
                             if x["kind"] == "geometry"}
        rays_by_key = {(x["shape"], x["index"]): x for x in records if x["kind"] == "ray"}
        for line in args.transform_dump.read_text().splitlines():
            kind, shape, index, *hex_values = line.split()
            shape, index = int(shape), int(index)
            if kind == "C":
                expected = placed(controls_by_shape[shape][index])
            elif kind == "O":
                expected = placed(rays_by_key[shape, index]["origin"])
            elif kind == "D":
                expected = rotate(rays_by_key[shape, index]["direction"])
            else:
                raise ValueError("unknown C++ payload kind")
            if [float.fromhex(x).hex() for x in hex_values] != [float(x).hex() for x in expected]:
                raise ValueError(f"C++ binary transform mismatch: {kind} {shape} {index}")
            verified_transform_values += len(hex_values)
    geometries = {x["shape"]: (spans([placed(p) for p in x["controls"]]
                                   if args.rigid else x["controls"]), F(x["radius"]))
                  for x in records if x["kind"] == "geometry"}
    report = {"schema": "stellarcsg-exact-circular-oracle-v1",
              "authority": "exact rational cardinal spline of binary64 input controls and ray line",
              "scope": "constant circular tube boundary root isolation; no geometry admissibility certificate",
              "capture_sha256": hashlib.sha256(raw).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "comparison_tolerance": "2e-7*max(1,nearest_distance), unchanged original oracle contract",
              "strict_absolute_comparison_tolerance": "2e-8 cm, reported separately without loosening",
              "rigid_reconstruction": args.rigid,
              "verified_cpp_transform_values": verified_transform_values,
              "arithmetic_audit": {
                  "coefficient_trimming": "Only exact trailing zero coefficients removed; no magnitude threshold",
                  "near_real_candidates": "No complex-root imaginary cutoff; exact Sturm counts distinct real roots",
                  "degeneracy": "Exact GCD(A,B); exact discriminant GCD/sign isolates tangent exceptional roots",
                  "root_recovery": "Rational interval division and integer-square-root enclosures; unresolved budgets raise",
                  "classification": "Boundary-root comparison only; does not certify solid injectivity or elliptic sections"},
              "results": []}
    with args.output.open("x", encoding="utf8") as handle:
        for item in records:
            if item["kind"] != "ray":
                continue
            key = item["shape"], item["index"]
            if key not in blocked:
                continue
            if args.shape is not None and item["shape"] != args.shape:
                continue
            if args.index is not None and item["index"] != args.index:
                continue
            start = time.monotonic()
            row = {"shape": key[0], "index": key[1], "original": item,
                   "previous_warnings": blocked[key]["oracle_warnings"]}
            origin = placed(item["origin"]) if args.rigid else item["origin"]
            direction = rotate(item["direction"]) if args.rigid else item["direction"]
            observed_distance = item["rigid_distance"] if args.rigid else item["distance"]
            row["input_origin_hex"] = [float(x).hex() for x in origin]
            row["input_direction_hex"] = [float(x).hex() for x in direction]
            try:
                nearest, roots, diagnostics = exact_query(
                    *geometries[key[0]], origin, direction)
                row["nearest_enclosure"] = float_interval(nearest) if nearest else None
                row["root_enclosures"] = [
                    {"t": float_interval(t), "span": span, "u": float_interval(u), "kind": kind,
                     "exact_t_interval": [str(x) for x in t],
                     "exact_u_interval": [str(x) for x in u]}
                    for t, span, u, kind in roots]
                row["exact_diagnostics"] = diagnostics
                row["isolation_state"] = "PASS"
                if (observed_distance is not None) != bool(nearest):
                    row["comparison_state"] = "FAIL"
                    row["strict_2e8_absolute_state"] = "FAIL"
                    row["disposition"] = "production_hit_classification_disagrees_with_exact_input_geometry"
                elif nearest:
                    actual = F(observed_distance)
                    error = (nearest[0]-actual, nearest[1]-actual)
                    row["signed_oracle_minus_production_error"] = float_interval(error)
                    tolerance = F(2, 10**7)*max(F(1), abs(nearest[0]), abs(nearest[1]))
                    row["comparison_state"] = ("PASS" if max(abs(error[0]), abs(error[1]))
                                               <= tolerance else "FAIL")
                    row["disposition"] = "exact_input_root_resolved"
                    row["strict_2e8_absolute_state"] = ("PASS"
                        if max(abs(error[0]), abs(error[1])) <= F(2, 10**8) else "FAIL")
                else:
                    row["comparison_state"] = "PASS"
                    row["strict_2e8_absolute_state"] = "PASS"
                    row["disposition"] = "exact_input_no_forward_root"
            except (ArithmeticError, ValueError) as error:
                row.update(isolation_state="BLOCKED", comparison_state="BLOCKED",
                           strict_2e8_absolute_state="BLOCKED",
                           disposition=str(error))
            row["elapsed_seconds"] = time.monotonic()-start
            report["results"].append(row)
            print(json.dumps({k: row[k] for k in ("shape", "index", "isolation_state",
                                                 "comparison_state", "elapsed_seconds")}), flush=True)
        report["counts"] = {
            criterion: {state: sum(row[criterion] == state for row in report["results"])
                        for state in ("PASS", "FAIL", "BLOCKED", "NOT_RUN")}
            for criterion in ("isolation_state", "comparison_state", "strict_2e8_absolute_state")}
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return 1 if any(row["comparison_state"] == "FAIL" or row["strict_2e8_absolute_state"] == "FAIL"
                    for row in report["results"]) else (
        2 if any(row["comparison_state"] == "BLOCKED" for row in report["results"]) else 0)


if __name__ == "__main__":
    raise SystemExit(main())
