#!/usr/bin/env python3
"""Exact analytic counterexamples and admission-predicate audit, not a solver.

Uses only Python's standard library. Reference polynomials are explicitly
factorized; no sampled root finder supplies the expected answers. Predicate
models are labeled separately from execution of production code.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PIN = "c08eea92ca3fb63eb8adbf44cfb4ea8612639e30"
EXACT_REF = "5ed327ade33b31ecdb5e3b4b4111c55f321991fd"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def binary(value):
    return Q.from_float(float(value))


def polynomial_hull(coefficients):
    """Exact power-to-Bernstein hull on [0,1]. Mirrors reference formula."""
    degree = len(coefficients) - 1
    bernstein = [sum((coefficients[k] * Q(math.comb(i, k),
                     math.comb(degree, k)) for k in range(i + 1)), Q(0))
                 for i in range(degree + 1)]
    return min(bernstein), max(bernstein)


def imul(a, b):
    products = [x*y for x in a for y in b]
    return min(products), max(products)


def separation_witness():
    """Reproduce only the archived reference's center-separation predicate.

    This does NOT certify regularity/curvature, run ray roots, or infer physical
    self-intersection. It explains a sufficient-certificate rejection.
    """
    data = json.loads((HERE / "retained_shape2_controls.json").read_text())
    points = [[binary(v) for v in p] for p in data["controls"]]
    n = len(points)
    numerator = ((1, 4, 1, 0), (-3, 0, 3, 0),
                 (3, -6, 3, 0), (-1, 3, -3, 1))
    spans = []
    for i in range(n):
        center_box, tangent_box = [], []
        for axis in range(3):
            p = [sum((points[(i+k-1) % n][axis] * numerator[j][k]
                      for k in range(4)), Q(0)) / 6 for j in range(4)]
            # Match reference trim: lower polynomial degree can tighten hulls.
            while len(p) > 1 and p[-1] == 0:
                p.pop()
            d = [k*p[k] for k in range(1, len(p))] or [Q(0)]
            center_box.append(polynomial_hull(p))
            tangent_box.append(polynomial_hull(d))
        spans.append((center_box, tangent_box))
    threshold = 4 * binary(data["radius"])**2
    visited = 0
    for i in range(n):
        for j in range(i, n):
            visited += 1
            distance_squared = sum((max(Q(0), a[0]-b[1], b[0]-a[1])**2
                for a,b in zip(spans[i][0], spans[j][0])), Q(0))
            if distance_squared > threshold:
                continue
            forward, reverse = j-i, n-(j-i)
            start = i if forward <= reverse else j
            steps = min(forward, reverse)
            cone = list(spans[start][1])
            for step in range(1, steps+1):
                next_box = spans[(start+step) % n][1]
                cone = [(min(a[0], b[0]), max(a[1], b[1]))
                        for a,b in zip(cone, next_box)]
            # INDEPENDENT interval multiplication: dot_box(cone,cone), not
            # square(). Negative lower bounds do not mean ||C'||^2 is negative.
            dot_lower = sum((imul(a,a)[0] for a in cone), Q(0))
            if dot_lower <= 0:
                return {
                    "pair": [i,j], "pairs_visited": visited,
                    "box_distance_squared_exact": str(distance_squared),
                    "box_distance_squared_float": float(distance_squared),
                    "four_radius_squared_exact": str(threshold),
                    "independent_cone_dot_lower_exact": str(dot_lower),
                    "independent_cone_dot_lower_float": float(dot_lower),
                    "cone_bounds_exact": [[str(x) for x in a] for a in cone],
                    "block_reason": "STELLARCSG_UNRESOLVED_CIRCULAR_TUBE: "
                        "embedded circular-tube separation certificate failed",
                    "meaning": "sufficient separation certificate fails; physical validity unresolved",
                    "reference_commit": EXACT_REF,
                }
    raise AssertionError("expected retained shape-2 rejection did not reproduce")


def run_cases():
    records = []
    def add(name, outcome="COUNTEREXAMPLE_CONFIRMED", **values):
        records.append({"case": name, "outcome": outcome, **values})
    grid = [Q(i,8) for i in range(9)]
    a = Q(3,16)
    f = lambda t: (t-a)**2
    check(f(a) == 0 and all(f(t) > 0 for t in grid), "even-root witness")
    add("even_root_between_scan_points", root=str(a), exact_sample_signs=[1]*9,
        execution="exact analytic example of the eight-segment fallback limitation")

    delta = Q(1,2**30)
    f = lambda t: (t-a)**2 - delta**2
    check(all(f(t)>0 for t in grid) and f(a-delta)==f(a+delta)==0,
          "near-multiplicity witness")
    add("two_simple_roots_between_scan_points", roots=[str(a-delta),str(a+delta)],
        exact_sample_signs=[1]*9)

    early, late = Q(3,16), Q(3,4)
    f = lambda t: (t-early)**2 * (t-late)
    signs = [int(f(t)>0)-int(f(t)<0) for t in grid]
    check(f(early)==0 and f(late)==0 and signs[1]==signs[2]==-1,
          "earlier even-root prefix witness")
    add("earlier_even_root_before_later_crossing", nearest=str(early), later=str(late),
        exact_sample_signs=signs)

    roots = [Q(1,16), Q(3,32), Q(3,4)]
    f = lambda t: math.prod(t-r for r in roots)
    check(all(f(r)==0 for r in roots) and f(grid[0])<0 and f(grid[1])<0,
          "hidden earlier simple pair")
    add("earlier_simple_pair_before_later_crossing", roots=[str(x) for x in roots])

    # Both source branch predicates are exercised as MODELS, not a full kernel run.
    zero_proxy_queued = (not False) and (0 != 0)
    later_seed_queued = (not True) and (1 != 0)
    check(not zero_proxy_queued and not later_seed_queued, "queue predicate changed")
    add("zero_proxy_and_solved_prefix_queue_predicates", execution="source predicate model",
        zero_proxy_retained=False, successful_seed_prefix_retained=False)

    tolerance = Q(1,2**20)
    epsilon = Q(1,2**80)
    check(epsilon > 0 and epsilon < tolerance, "residual witness")
    add("small_residual_with_no_root", polynomial="(t-3/16)^2 + 2^-80",
        min_residual=str(epsilon), real_roots=0)

    s = Q(5,128)
    knots = [Q(i,64) for i in range(65)]
    check(all(2*(t-s) != 0 for t in knots) and 2*(s-s)==0, "hidden derivative zero")
    add("whole_span_center_regularity", center="((u-5/128)^2,0,0)",
        singular_parameter=str(s), sampled_derivatives_nonzero=65)
    check(all(t-s != 0 for t in knots), "hidden frame zero")
    add("whole_span_normal_independence", center="(u,0,0)",
        supplied_normal="(1,u-5/128,0)", singular_parameter=str(s))

    # Reference contract distinction: t=0 is omitted by the archived ordinary
    # STRICT-POSITIVE solve. A contact-aware closed-domain API could report it
    # separately. No assertion that current API must return zero is made.
    push = Q(1,2**20)
    second = push/2
    mathematical_roots = [Q(0), second]
    strict_forward = [t for t in mathematical_roots if t>0]
    blanket_suppression = [t for t in mathematical_roots if t>push]
    check(strict_forward == [second] and blanket_suppression == [], "origin push witness")
    add("origin_association_not_distance_push", polynomial="t*(t-2^-21)",
        closed_domain_roots=[str(t) for t in mathematical_roots],
        strict_positive_root=str(second), minimum_t_push=str(push),
        pushed_result="NO_HIT", execution="analytic contact-contract model")

    near_positive = Q(3,2**55)
    check(float(near_positive)==8.326672684688674e-17 and near_positive>0,
          "a06 reference distance")
    add("a06_is_positive_not_exact_zero", outcome="HISTORICAL_RECORD_INTERPRETATION",
        recorded_distance=float(near_positive), exact_value_of_recorded_double=str(near_positive),
        new_ray_solver_execution=False)

    # A plane is a valid degree-elevated bicubic patch. Its projected Newton
    # residual is not a longitudinal error bound; no Bezier implementation run.
    delta = Q(1,2**40)
    u_star, u_guess = Q(1,4), Q(3,4)
    residual = delta*(u_guess-u_star)
    check(residual<Q(1,10**10) and u_guess-u_star==Q(1,2), "longitudinal witness")
    add("projected_patch_residual_not_t_certificate",
        surface="(2^-40*(u-1/4),v,u)", ray="(0,0,t)",
        exact_t=str(u_star), candidate_t=str(u_guess), t_error=str(u_guess-u_star),
        projected_residual_exact=str(residual), projected_residual_float=float(residual),
        execution="analytic affine patch, not an unpublished Bezier implementation")

    # Exact signed-permutation rigid transform and power-of-two direction scales.
    center = [Q(0)]*3
    origin = [Q(2),Q(0),Q(0)]
    translation = [Q(8),Q(-4),Q(2)]
    rot = lambda p: [-p[1],p[0],p[2]]
    oc = [a+b for a,b in zip(rot(origin),translation)]
    cc = [a+b for a,b in zip(rot(center),translation)]
    for k in [Q(1,4),Q(1),Q(4)]:
        direction = [Q(0),-k,Q(0)]
        lam = Q(1)/k
        point = [o+lam*d for o,d in zip(oc,direction)]
        check(sum((x-y)**2 for x,y in zip(point,cc))==1 and lam*k==1,
              "exact transform/scale fixture")
    add("exact_rigid_and_direction_scaling", outcome="ANALYTIC_CONTROL_CONFIRMED",
        physical_distance=1, ray_parameters=[4,1,0.25], direction_scales=[0.25,1,4])

    check(float(2**54+1)==float(2**54), "translation rounding witness")
    add("rounded_rigid_transform_is_new_input", translation=2**54,
        original_separation=1, stored_separation=0)

    # The knot tests can pass while an inter-knot point disagrees. This is a
    # sampled-equality counterexample, not a reimplementation of torus distance.
    n = 64
    controls = [(5*math.cos(2*math.pi*i/n),5*math.sin(2*math.pi*i/n))
                for i in range(n)]
    knots_xy = [tuple((controls[(i-1)%n][j]+4*controls[i][j]+controls[(i+1)%n][j])/6
                     for j in range(2)) for i in range(n)]
    radii = [math.hypot(*p) for p in knots_xy]
    mean = sum(radii)/n
    midpoint = tuple((controls[-1][j]+23*controls[0][j]+23*controls[1][j]+controls[2][j])/48
                     for j in range(2))
    mismatch = abs(math.hypot(*midpoint)-mean)
    check(max(abs(r-mean) for r in radii)<1e-6*5.25 and mismatch>1e-8,
          "sampled exact-torus specialization witness")
    add("sampled_torus_specialization_not_identity", knot_radius_mean=mean,
        max_knot_radius_deviation=max(abs(r-mean) for r in radii),
        inter_knot_radius_mismatch=mismatch,
        execution="constructor-predicate numerical illustration plus polynomial-identity argument")

    false_hit = Q(1, 10**12)
    expected = Q(1, 500)
    allowance = Q(2, 10**10)
    old_pass = false_hit > 0 and false_hit <= expected + allowance
    corrected_pass = abs(false_hit - expected) <= allowance
    check(old_pass and not corrected_pass, "one-sided near-entry test witness")
    add("one_sided_near_entry_test_accepts_wrong_hit",
        reported_distance=str(false_hit), expected_distance=str(expected),
        existing_upper_bound_test_passes=old_pass,
        two_sided_accuracy_test_passes=corrected_pass,
        execution="test-predicate model; no manufactured solver output")

    witness = separation_witness()
    add("retained_shape2_separation_predicate", outcome="BLOCKED_REASON_REPRODUCED", **witness)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = run_cases()
    result = {
        "pinned_commit": PIN,
        "purpose": "audit witnesses; success does NOT mean solver qualification",
        "cases": records,
        "case_count": len(records),
        "python": sys.version,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "retained_fixture_sha256": hashlib.sha256((HERE/"retained_shape2_controls.json").read_bytes()).hexdigest(),
        "full_kernel_executed": False,
        "geometry_performance": {"distance_ns_per_query": None,
            "classification_ns_per_query": None,"normal_ns_per_query": None,
            "distance_candidate_over_ztorus": None,
            "classification_candidate_over_ztorus": None,
            "normal_candidate_over_ztorus": None,"transport_histories_per_second": None,
            "throughput_candidate_over_ztorus": None,"candidate_over_old_fast": None,
            "repeated_run_variability": None,
            "status": "INCOMPLETE_NOT_MEASURED; native OpenMC ZTorus unavailable; no performance claims"},
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(f"{len(records)} audit witnesses/controls evaluated; full solver not executed.")
    print(json.dumps(records[-1],indent=2))

if __name__ == "__main__":
    main()
