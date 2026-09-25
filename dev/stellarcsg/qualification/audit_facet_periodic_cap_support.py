"""Measure sampled x/y cap-outline mismatch after a 90-degree rotation."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bitwise_triangle_keys(projected: np.ndarray) -> set:
    bits = np.asarray(projected, dtype="<f8").view("<u8").reshape(-1, 3, 2)
    return {tuple(sorted(tuple(map(int, vertex)) for vertex in triangle))
            for triangle in bits}


def boundary_edges(vertices: np.ndarray, axis: int):
    cap = vertices[np.max(np.abs(vertices[:, :, axis]), axis=1) <= 1e-10]
    projected = cap[:, :, [1, 2] if axis == 0 else [0, 2]]
    counts: Counter = Counter()
    edges = {}
    third_vertices = {}
    for triangle in projected:
        for i, j, k in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
            a = tuple(0.0 if x == 0 else float(x) for x in triangle[i])
            b = tuple(0.0 if x == 0 else float(x) for x in triangle[j])
            key = tuple(sorted((a, b)))
            counts[key] += 1
            edges[key] = (a, b)
            third_vertices[key] = tuple(triangle[k])
    if any(count not in (1, 2) for count in counts.values()):
        raise ValueError("non-manifold planar cap triangulation")
    boundary = [key for key, count in counts.items() if count == 1]
    return (np.asarray([edges[key] for key in boundary], dtype=float),
            np.asarray([third_vertices[key] for key in boundary], dtype=float),
            projected)


def inside_cap(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    p = points[:, None, :]
    a = triangles[None, :, 0, :]
    u = triangles[None, :, 1, :] - a
    v = triangles[None, :, 2, :] - a
    q = p - a
    determinant = u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]
    s = (q[..., 0] * v[..., 1] - q[..., 1] * v[..., 0]) / determinant
    t = (u[..., 0] * q[..., 1] - u[..., 1] * q[..., 0]) / determinant
    return np.any((s >= -1e-12) & (t >= -1e-12)
                  & (s + t <= 1.0 + 1e-12), axis=1)


def near_outline_disagreement(source: np.ndarray, third: np.ndarray,
                              source_triangles: np.ndarray,
                              target_triangles: np.ndarray) -> dict:
    midpoint = np.mean(source, axis=1)
    edge = source[:, 1, :] - source[:, 0, :]
    inward = np.column_stack((-edge[:, 1], edge[:, 0]))
    inward /= np.linalg.norm(inward, axis=1)[:, None]
    inward *= np.where(np.sum((third - midpoint) * inward, axis=1) >= 0.0,
                       1.0, -1.0)[:, None]
    result = {}
    for offset_cm in (1e-5, 1e-4, 5e-4, 1e-3):
        points = midpoint + offset_cm * inward
        source_inside = inside_cap(points, source_triangles)
        target_inside = inside_cap(points, target_triangles)
        result[str(offset_cm)] = {
            "source_inside": int(np.count_nonzero(source_inside)),
            "target_outside": int(np.count_nonzero(source_inside & ~target_inside))}
    return result


def point_to_segments(points: np.ndarray, edges: np.ndarray) -> np.ndarray:
    p = points[:, None, :]
    a = edges[None, :, 0, :]
    direction = edges[None, :, 1, :] - a
    t = np.clip(np.sum((p - a) * direction, axis=2)
                / np.sum(direction * direction, axis=2), 0.0, 1.0)
    return np.sqrt(np.min(np.sum((p - (a + t[:, :, None] * direction))**2,
                                 axis=2), axis=1))


def sampled_directed_gap(source: np.ndarray, target: np.ndarray) -> dict:
    fractions = np.linspace(0.0, 1.0, 65)
    points = (source[:, 0, None, :] * (1.0 - fractions)[None, :, None]
              + source[:, 1, None, :] * fractions[None, :, None]).reshape(-1, 2)
    distances = point_to_segments(points, target)
    return {"sample_count": len(points),
            "maximum_cm": float(np.max(distances)),
            "p99_cm": float(np.quantile(distances, 0.99)),
            "mean_cm": float(np.mean(distances)),
            "above_1e-8_cm": int(np.count_nonzero(distances > 1e-8))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--payload-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output file must be new")
    prior = json.loads(args.payload_receipt.read_text())
    if (prior["schema"] not in (
            "stellarcsg.p00-facet-payload/v1",
            "stellarcsg.periodic-p00-facet-candidate/v1")
            or prior["output_h5_sha256"] != sha256(args.payload)):
        raise ValueError("P00 payload hash differs from receipt")
    with h5py.File(args.payload, "r") as handle:
        vertices = handle["facets/one_period/triangle_vertices"][:]
    x_edges, x_third, x_triangles = boundary_edges(vertices, 0)
    y_edges, y_third, y_triangles = boundary_edges(vertices, 1)
    if len(x_edges) != 80 or len(y_edges) != 80:
        raise ValueError("unexpected P00 cap boundary edge count")
    x_cap = vertices[np.max(np.abs(vertices[:, :, 0]), axis=1) <= 1e-10]
    y_cap = vertices[np.max(np.abs(vertices[:, :, 1]), axis=1) <= 1e-10]
    x_triangle_keys = bitwise_triangle_keys(x_cap[:, :, [1, 2]])
    y_triangle_keys = bitwise_triangle_keys(y_cap[:, :, [0, 2]])
    bitwise_cap_match = (len(x_triangle_keys) == 80
                         and x_triangle_keys == y_triangle_keys)
    x_to_y = sampled_directed_gap(x_edges, y_edges)
    y_to_x = sampled_directed_gap(y_edges, x_edges)
    outline_disagreement = {
        "x_to_y": near_outline_disagreement(x_edges, x_third,
                                             x_triangles, y_triangles),
        "y_to_x": near_outline_disagreement(y_edges, y_third,
                                             y_triangles, x_triangles)}
    state = ("PERIODIC_CAP_TRIANGLES_BITWISE_MATCH" if bitwise_cap_match
             else "PERIODIC_CAP_OUTLINES_DIFFER"
             if max(x_to_y["maximum_cm"], y_to_x["maximum_cm"]) > 1e-8
             else "NO_SAMPLED_CAP_DIFFERENCE")
    receipt = {
        "schema": "stellarcsg.facet-periodic-cap-support/v1",
        "state": state,
        "payload_classification": prior["classification"],
        "bitwise_rotated_cap_triangle_match": bitwise_cap_match,
        "rotation_map": "x=0 cap (y,z) maps to y=0 cap (x,z)",
        "boundary_edge_count": {"x_zero": len(x_edges),
                                "y_zero": len(y_edges)},
        "directed_sampled_gap": {"x_to_y": x_to_y, "y_to_x": y_to_x},
        "near_outline_coverage": outline_disagreement,
        "hashes": {"payload": sha256(args.payload),
                   "payload_receipt": sha256(args.payload_receipt),
                   "auditor": sha256(Path(__file__))},
        "claim_boundary": "Triangle equality compares unordered projected cap vertex triples bitwise after rotation. Distances sample 65 points per boundary edge; inward offsets test coverage near each edge midpoint. An exact triangle match applies only to this faceted representation and does not establish continuous-CAD equivalence or transport correctness."
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": state,
                      "max_gap_cm": max(x_to_y["maximum_cm"],
                                        y_to_x["maximum_cm"])}))


if __name__ == "__main__":
    main()
