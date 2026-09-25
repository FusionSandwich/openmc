"""Exact rational fixtures only; not a general geometry implementation.

The two slab near-entry cases exercise the same earlier-entry bookkeeping pattern
as recovery04 a03/a04, without importing, rebuilding or rerunning WISTELL data.
Unit-sphere fixtures include a double root and unsuppressed/suppressed contact.
Irrational square roots deliberately return UNRESOLVED rather than a false miss.
"""
from fractions import Fraction
from math import isqrt


def rational_sqrt(value):
    if value < 0:
        return None
    n, d = isqrt(value.numerator), isqrt(value.denominator)
    return Fraction(n, d) if n * n == value.numerator and d * d == value.denominator else None


def solve(query, model):
    f = lambda x: Fraction(float(x))
    geom = model["geometries"][query["geometry"]]
    o, d = [f(x) for x in query["origin"]], [f(x) for x in query["direction"]]
    norm = rational_sqrt(sum(x * x for x in d))
    if norm is None or norm == 0:
        return "UNRESOLVED", None, "FIXTURE_DIRECTION_NORM_NOT_EXACT_RATIONAL"
    if geom["type"] == "slab":
        axis = geom["axis"]
        if d[axis] == 0:
            return "MISS", None, None
        roots = [(f(face) - o[axis]) / d[axis] for face in (geom["lo_cm"], geom["hi_cm"])]
    elif geom["type"] == "sphere":
        o = [x - f(c) for x, c in zip(o, geom["center_cm"])]
        a = sum(x * x for x in d)
        b = 2 * sum(x * y for x, y in zip(o, d))
        c = sum(x * x for x in o) - f(geom["radius_cm"]) ** 2
        disc = b * b - 4 * a * c
        if disc < 0:
            return "MISS", None, None
        sq = rational_sqrt(disc)
        if sq is None:
            return "UNRESOLVED", None, "FIXTURE_ROOT_NOT_EXACT_RATIONAL"
        roots = [(-b - sq) / (2 * a), (-b + sq) / (2 * a)]
    else:
        return "UNRESOLVED", None, "GEOMETRY_OUTSIDE_FIXTURE_DOMAIN"
    roots = [t for t in roots if t >= 0 and not (query["coincident"] and t == 0)]
    if not roots:
        return "MISS", None, None
    exact = min(roots) * norm
    rounded = float(exact)
    if Fraction(rounded) != exact:
        return "UNRESOLVED", None, "FIXTURE_DISTANCE_NOT_EXACT_BINARY64"
    return "HIT", rounded, None


def fixture_data():
    model = {"schema": "stellarcsg.analytic-model/v1", "domain": "exact-rational-test-fixtures-only",
             "physical_assembly_qualified": False,
             "geometries": {"slab": {"type": "slab", "axis": 0, "lo_cm": 0, "hi_cm": 1},
                            "sphere": {"type": "sphere", "center_cm": [0, 0, 0], "radius_cm": 1}}}
    specifications = [
        ("near-entry", "slab", [-.25, 0, 0], [1, 0, 0], False, "HIT", .25),
        ("earlier-entry", "slab", [-.75, 0, 0], [1, 0, 0], False, "HIT", .75),
        ("sphere-enter", "sphere", [-2, 0, 0], [1, 0, 0], False, "HIT", 1),
        ("even-root", "sphere", [-2, 1, 0], [1, 0, 0], False, "HIT", 2),
        ("clear-miss", "sphere", [-2, 2, 0], [1, 0, 0], False, "MISS", None),
        ("origin-contact", "sphere", [1, 0, 0], [1, 0, 0], False, "HIT", 0),
        ("suppressed-contact", "sphere", [1, 0, 0], [1, 0, 0], True, "MISS", None),
        ("direction-scaling", "sphere", [-2, 0, 0], [2, 0, 0], False, "HIT", 1),
    ]
    bank = {"schema": "stellarcsg.query-bank/v1", "queries": []}
    for id_, geometry, origin, direction, coincident, result, distance in specifications:
        bank["queries"].append({"id": id_, "geometry": geometry, "category": id_,
                                "origin": origin, "direction": direction, "coincident": coincident,
                                "expected": {"result": result, "distance_cm": distance,
                                             "provenance": "Exact rational plane/unit-sphere calculation; no spline or physical-assembly claim"}})
    return model, bank
