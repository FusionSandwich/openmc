"""Independent sampled polynomial oracle for test_swept_adversarial.cpp JSONL.

Enumerates original cubic centerline controls without production BVHs, projection,
frames, or reference routines. NumPy roots and SciPy corrections are numerical
evidence, NOT a mathematical completeness guarantee. Geometry 2 is an unqualified
high-curvature stress case; its results do not qualify an engineering geometry.
No input is modified and the output must not already exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy.polynomial import Polynomial as P
from scipy.optimize import root


def span_polynomials(controls):
    """Direct cardinal-basis expression independent of production conversion."""
    u = P([0., 1.])
    basis = [(1-u)**3/6, (3*u**3-6*u**2+4)/6,
             (-3*u**3+3*u**2+3*u+1)/6, u**3/6]
    return [[sum((basis[a]*controls[(i+a-1) % len(controls), axis]
                  for a in range(4)), P([0.])) for axis in range(3)]
            for i in range(len(controls))]


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), P([0.]))


def polynomial_roots(poly, warnings):
    coefficients = np.array(poly.coef, dtype=float)
    scale = max(float(np.max(np.abs(coefficients))), np.finfo(float).tiny)
    while len(coefficients) > 1 and abs(coefficients[-1]) < 1e-14*scale:
        coefficients = coefficients[:-1]
    if len(coefficients) <= 1:
        return []
    values = P(coefficients/scale).roots()
    result = []
    for value in values:
        if -1e-7 <= value.real <= 1+1e-7:
            if abs(value.imag) <= 1e-7:
                result.append(float(np.clip(value.real, 0, 1)))
            elif abs(value.imag) <= 1e-5:
                warnings.append("near_real_polynomial_root")
    return result


def nearest(spans, radius, origin, direction):
    """Eliminate ray distance from tube radius and tangent-orthogonality equations.

    A=d.c', B=(o-c).c', D=d.(o-c), E=|o-c|^2-r^2.
    P=B^2-2ABD+A^2E; recover t=-B/A, and verify the original equations.
    A=0 needs separate B roots and the t quadratic. No production classification
    is used, including for final root residuals.
    """
    direction = direction / np.linalg.norm(direction)
    candidates, warnings = [], []
    for span_id, c in enumerate(spans):
        derivative = [axis.deriv() for axis in c]
        offset = [origin[axis]-c[axis] for axis in range(3)]
        a, b = dot(direction, derivative), dot(offset, derivative)
        d, e = dot(direction, offset), dot(offset, offset)-radius**2
        a_zero = np.max(np.abs(a.coef)) <= 1e-13
        b_zero = np.max(np.abs(b.coef)) <= 1e-13
        if a_zero and b_zero:
            warnings.append("identically_degenerate_span")
            continue
        polynomial = b if a_zero else b*b-2*a*b*d+a*a*e
        us = polynomial_roots(polynomial, warnings)
        # Endpoint ownership is independent of production seed order.
        us += [0., 1.]
        for u in us:
            av, bv, dv, ev = (float(f(u)) for f in (a, b, d, e))
            starts = []
            if abs(av) > 1e-10:
                starts = [-bv/av]
            elif abs(bv) <= 1e-7:
                discriminant = dv*dv-ev
                if discriminant >= -1e-12:
                    square = np.sqrt(max(discriminant, 0.))
                    starts = [-dv-square, -dv+square]
            for t in starts:
                def function(x):
                    uu, tt = x
                    center = np.array([f(uu) for f in c])
                    first = np.array([f(uu) for f in derivative])
                    radial = origin+tt*direction-center
                    return [np.dot(radial, first),
                            np.dot(radial, radial)-radius**2]
                initial_residual = np.linalg.norm(function([u, t]))
                correction = root(function, [u, t], method="hybr", tol=1e-11)
                uu, tt = correction.x
                residual = np.linalg.norm(function([uu, tt]))
                if not np.isfinite(residual) or residual > 2e-9 or not -1e-8 <= uu <= 1+1e-8:
                    if initial_residual < 1e-6:
                        warnings.append("unresolved_polynomial_candidate")
                    continue
                if tt <= 1e-9:
                    continue
                first = np.array([f(uu) for f in derivative])
                second = np.array([f.deriv()(uu) for f in derivative])
                radial = origin+tt*direction-np.array([f(uu) for f in c])
                jacobian = np.array([
                    [np.dot(radial, second)-np.dot(first, first),
                     np.dot(direction, first)],
                    [-2*np.dot(radial, first), 2*np.dot(radial, direction)]])
                # A tiny residual near a double root can also be a near miss.
                # Preserve it as unresolved rather than inventing an oracle hit.
                if np.linalg.cond(jacobian) > 1e7:
                    warnings.append("ill_conditioned_tangent_candidate")
                if not correction.success:
                    warnings.append("local_correction_did_not_converge")
                candidates.append((float(tt), span_id, float(uu), float(residual)))
    candidates.sort()
    unique = []
    for candidate in candidates:
        if not unique or candidate[0]-unique[-1][0] > 1e-7:
            unique.append(candidate)
    return unique, sorted(set(warnings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.capture.read_bytes()
    geometries, verdicts = {}, []
    for line in raw.splitlines():
        item = json.loads(line)
        if item["kind"] == "geometry":
            geometries[item["shape"]] = (
                span_polynomials(np.array(item["controls"])), item["radius"])
            continue
        if item["kind"] != "ray":
            continue
        spans, radius = geometries[item["shape"]]
        roots, warnings = nearest(spans, radius, np.array(item["origin"]),
                                  np.array(item["direction"]))
        expected = roots[0][0] if roots else None
        error = None
        state = "PASS"
        if "error" in item or warnings:
            state = "BLOCKED"
        elif bool(roots) != item["found"]:
            state = "FAIL"
        elif expected is not None:
            if item["distance"] is None:
                state = "FAIL"
            else:
                error = abs(item["distance"]-expected)
                if error > 2e-7*max(1., abs(expected)):
                    state = "FAIL"
        verdicts.append(dict(item, oracle_state=state, oracle_nearest=expected,
                             distance_error=error, oracle_roots=roots,
                             oracle_warnings=warnings))
    counts = {state: sum(row["oracle_state"] == state for row in verdicts)
              for state in ("PASS", "FAIL", "BLOCKED", "NOT_RUN")}
    report = {
        "schema": "stellarcsg-swept-adversarial-v1",
        "oracle_status": "sampled floating-point polynomial evidence; no completeness guarantee",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "oracle_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "absolute_or_relative_distance_tolerance": 2e-7,
        "shape_2_admissibility": "unqualified high-curvature stress case",
        "counts": counts, "results": verdicts,
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(counts))
    return 1 if counts["FAIL"] else 2 if counts["BLOCKED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
