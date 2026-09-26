"""Certify cross-component facet intersections using exact stored coordinates."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


ACCEPTED_SHA256 = "126fdbec0a5795036ad75c7409f760652e47722d02f28fada89ddaf2fa71d9df"
DERIVED_SHA256 = "3db1723d250319d7e6e3d0a4cbbba7b88a68c830fba4214d001a8c2c2545c2d4"
ACCEPTED_H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def det(a, b, c):
    return dot(a, cross(b, c))


def exact_triangle(vertices):
    return [tuple(Fraction.from_float(float(x)) for x in point)
            for point in vertices]


def separated_exact(a, b):
    """Return a strict rational separating-axis witness, if found."""
    ea = [sub(a[(k + 1) % 3], a[k]) for k in range(3)]
    eb = [sub(b[(k + 1) % 3], b[k]) for k in range(3)]
    na, nb = cross(ea[0], ea[1]), cross(eb[0], eb[1])
    axes = [na, nb]
    axes += [cross(x, y) for x in ea for y in eb]
    axes += [cross(na, x) for x in ea]
    axes += [cross(nb, y) for y in eb]
    for index, axis in enumerate(axes):
        if axis == (0, 0, 0):
            continue
        pa = [dot(point, axis) for point in a]
        pb = [dot(point, axis) for point in b]
        if max(pa) < min(pb) or max(pb) < min(pa):
            return index
    return None


def strict_edge_face_witnesses(a, b):
    """Return all exact open-segment/open-triangle intersections."""
    u, v = sub(b[1], b[0]), sub(b[2], b[0])
    nu, nv = tuple(-x for x in u), tuple(-x for x in v)
    witnesses = []
    for edge in range(3):
        p, q = a[edge], a[(edge + 1) % 3]
        e, rhs = sub(q, p), sub(b[0], p)
        denominator = det(e, nu, nv)
        if denominator == 0:
            continue
        t = det(rhs, nu, nv) / denominator
        alpha = det(e, rhs, nv) / denominator
        beta = det(e, nu, rhs) / denominator
        if 0 < t < 1 and 0 < alpha and 0 < beta and alpha + beta < 1:
            location = tuple(p[k] + t*e[k] for k in range(3))
            witnesses.append((location, {
                "edge": edge, "t": float(t), "alpha": float(alpha),
                "beta": float(beta),
                "barycentric_slack": float(1 - alpha - beta),
                "point_cm": [float(x) for x in location],
                "exact_strict_interior": True}))
    return witnesses


def open_triangle_barycentrics(point, triangle):
    """Verify the point is exactly in a stored triangle's open face."""
    u, v, offset = sub(triangle[1], triangle[0]), sub(
        triangle[2], triangle[0]), sub(point, triangle[0])
    if dot(cross(u, v), offset) != 0:
        return None
    for first, second in ((0, 1), (0, 2), (1, 2)):
        denominator = u[first]*v[second] - u[second]*v[first]
        if denominator != 0:
            alpha = (offset[first]*v[second]
                     - offset[second]*v[first]) / denominator
            beta = (u[first]*offset[second]
                    - u[second]*offset[first]) / denominator
            return (alpha, beta) if (0 < alpha and 0 < beta
                                     and alpha + beta < 1) else None
    return None


def read_payload(path: Path):
    with h5py.File(path) as handle:
        group = handle["facets/one_period"]
        vertices = np.asarray(group["triangle_vertices"], dtype="<f8")
        components = np.asarray(group["component_ids"], dtype="<i4")
    if (vertices.shape != (3348, 3, 3)
            or components.shape != (3348,)
            or not np.isfinite(vertices).all()
            or set(components.tolist()) != set(range(8, 26))):
        raise ValueError("P00 facet payload shape or component IDs differ")
    return vertices, components


def audit(vertices, components):
    lower, upper = vertices.min(axis=1), vertices.max(axis=1)
    counts = Counter()
    separated = 0
    witnesses = []
    for first in range(8, 26):
        a_indices = np.flatnonzero(components == first)
        for second in range(first + 1, 26):
            b_indices = np.flatnonzero(components == second)
            boxes_overlap = np.all(
                (lower[a_indices, None] <= upper[None, b_indices])
                & (lower[None, b_indices] <= upper[a_indices, None]), axis=2)
            for a_local, b_local in zip(*np.where(boxes_overlap)):
                ai, bi = int(a_indices[a_local]), int(b_indices[b_local])
                counts[(first, second)] += 1
                a, b = exact_triangle(vertices[ai]), exact_triangle(vertices[bi])
                if separated_exact(a, b) is not None:
                    separated += 1
                    continue
                endpoints = [(point, "first_edge_second_face", row)
                             for point, row in strict_edge_face_witnesses(a, b)]
                endpoints += [(point, "second_edge_first_face", row)
                              for point, row in strict_edge_face_witnesses(b, a)]
                if len(endpoints) != 2 or endpoints[0][0] == endpoints[1][0]:
                    raise ValueError(f"triangle pair {ai}/{bi} is unresolved")
                midpoint = tuple((x + y)/2 for x, y in
                                 zip(endpoints[0][0], endpoints[1][0]))
                bary_a = open_triangle_barycentrics(midpoint, a)
                bary_b = open_triangle_barycentrics(midpoint, b)
                normal_a = cross(sub(a[1], a[0]), sub(a[2], a[0]))
                normal_b = cross(sub(b[1], b[0]), sub(b[2], b[0]))
                if (bary_a is None or bary_b is None
                        or cross(normal_a, normal_b) == (0, 0, 0)):
                    raise ValueError(f"triangle pair {ai}/{bi} is not transverse")
                witnesses.append({"component_ids": [first, second],
                                  "triangle_indices": [ai, bi],
                                  "intersection_endpoints": [
                                      {"direction": direction, **row}
                                      for _, direction, row in endpoints],
                                  "open_face_midpoint_cm": [float(x) for x in midpoint],
                                  "midpoint_barycentric_slack": [
                                      float(1 - sum(bary_a)),
                                      float(1 - sum(bary_b))],
                                  "exact_open_face_midpoint": True,
                                  "exact_nonparallel_normals": True})
    return {"triangle_aabb_candidate_pairs": sum(counts.values()),
            "component_pairs_with_triangle_aabb_overlap": len(counts),
            "component_pair_candidate_counts": {
                f"{a}-{b}": n for (a, b), n in sorted(counts.items())},
            "exact_separated_pairs": separated,
            "exact_strict_intersection_pairs": len(witnesses),
            "witnesses": witnesses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted", type=Path, required=True)
    parser.add_argument("--accepted-receipt", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--derived-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new file")
    accepted_receipt = json.loads(args.accepted_receipt.read_text())
    derived_receipt = json.loads(args.derived_receipt.read_text())
    if (sha256(args.accepted) != ACCEPTED_SHA256
            or sha256(args.derived) != DERIVED_SHA256
            or accepted_receipt["output_h5_sha256"] != ACCEPTED_SHA256
            or accepted_receipt["input_sha256"]["accepted_h5m"]
            != ACCEPTED_H5M_SHA256
            or derived_receipt["output_h5_sha256"] != DERIVED_SHA256
            or derived_receipt["input_hashes"]["accepted_payload"]
            != ACCEPTED_SHA256
            or derived_receipt["accepted_h5m_sha256"]
            != ACCEPTED_H5M_SHA256):
        raise ValueError("accepted or derived P00 lineage differs")
    original, original_ids = read_payload(args.accepted)
    derived, derived_ids = read_payload(args.derived)
    if not np.array_equal(original_ids, derived_ids):
        raise ValueError("component ID order differs")
    accepted_audit = audit(original, original_ids)
    derived_audit = audit(derived, derived_ids)
    expected_pairs = {(15, 16), (17, 18)}
    for label, result, expected_candidates, expected_separated in (
            ("accepted", accepted_audit, 691, 683),
            ("derived", derived_audit, 711, 703)):
        if (result["triangle_aabb_candidate_pairs"] != expected_candidates
                or result["exact_separated_pairs"] != expected_separated
                or result["exact_strict_intersection_pairs"] != 8
                or {tuple(row["component_ids"]) for row in result["witnesses"]}
                != expected_pairs):
            raise ValueError(f"{label} cross-component audit differs")
    for row in accepted_audit["witnesses"]:
        ai, bi = row["triangle_indices"]
        if (original[ai].tobytes() != derived[ai].tobytes()
                or original[bi].tobytes() != derived[bi].tobytes()):
            raise ValueError("intersecting facets changed in derived candidate")
    receipt = {
        "schema": "stellarcsg.p00-facet-component-overlap/v1",
        "state": "CONFIRMED_TRANSVERSE_OVERLAP_ACCEPTED_AND_DERIVED",
        "accepted": accepted_audit,
        "derived": derived_audit,
        "intersecting_triangle_pairs_bitwise_unchanged": True,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "accepted_payload": sha256(args.accepted),
                   "accepted_receipt": sha256(args.accepted_receipt),
                   "derived_payload": sha256(args.derived),
                   "derived_receipt": sha256(args.derived_receipt)},
        "claim_boundary": "Exact rational arithmetic on stored binary64 triangle vertices proves strict transverse surface intersections between component pairs 15-16 and 17-18 in both accepted and derived P00 faceted meshes. Each interior edge-face intersection of oriented closed shells implies local solid overlap. The audit does not quantify whole overlap volume, choose material priority, prove continuous-CAD overlap, or alter the accepted H5M."
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])


if __name__ == "__main__":
    main()
