"""Build a finite one-period inside/outside bank from accepted P00 facets.

Only the hashed facet catalog is queried. Mesh parity checks do not prove a
continuous CAD surface or qualify the StellarCSG distance/root solver.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


RAY_DIRECTIONS = np.asarray([
    [0.573, 0.711, 0.404],
    [0.797, -0.363, 0.483],
    [-0.299, 0.821, 0.486],
], dtype=np.float64)
RAY_DIRECTIONS /= np.linalg.norm(RAY_DIRECTIONS, axis=1)[:, None]
OFFSETS_CM = (0.05, 0.1, 0.2)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ray_hits(triangles: np.ndarray, point: np.ndarray,
             direction: np.ndarray) -> tuple[int, float, float]:
    """Count non-edge Moller-Trumbore hits on one closed facet group."""
    start = triangles[:, 0]
    edge1 = triangles[:, 1] - start
    edge2 = triangles[:, 2] - start
    cross = np.cross(direction, edge2)
    determinant = np.einsum("ij,ij->i", edge1, cross)
    nonparallel = np.abs(determinant) > 1.0e-12
    reciprocal = np.divide(1.0, determinant,
                           out=np.zeros_like(determinant), where=nonparallel)
    delta = point - start
    u = reciprocal * np.einsum("ij,ij->i", delta, cross)
    cross2 = np.cross(delta, edge1)
    v = reciprocal * np.einsum("ij,j->i", cross2, direction)
    distance = reciprocal * np.einsum("ij,ij->i", edge2, cross2)
    hit = (nonparallel & (u >= 0.0) & (v >= 0.0)
           & (u + v <= 1.0) & (distance > 1.0e-8))
    if not hit.any():
        return 0, 1.0, float("inf")
    bary_margin = float(min(np.min(u[hit]), np.min(v[hit]),
                            np.min(1.0 - u[hit] - v[hit])))
    return int(hit.sum()), bary_margin, float(np.min(distance[hit]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p00-build", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    catalog_path = args.p00_build / "magnet_boundary_facet_catalog.json"
    dagmc_path = args.p00_build / "dagmc.h5m"
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if (mapping["classification"]
            != "ACCEPTED_P00_H5M_LOCAL_FACET_ORDER_DIAGNOSTIC"
            or sha256(catalog_path) != mapping["input_sha256"]["facet_catalog"]
            or sha256(dagmc_path) != mapping["input_sha256"]["dagmc_h5m"]
            or catalog["dagmc_file"]["sha256"] != sha256(dagmc_path)
            or len(mapping["rows"]) != 18
            or len(catalog["magnets"]) != 18):
        raise ValueError("accepted mesh/catalog/mapping identity mismatch")

    rows = []
    smallest_bary_margin = 1.0
    smallest_hit_distance = float("inf")
    for source_row, magnet in zip(mapping["rows"], catalog["magnets"]):
        if source_row["dagmc_volume_id"] != magnet["dagmc_volume_id"]:
            raise ValueError("source-to-magnet mapping changed")
        triangles = np.asarray([
            facet["triangle_vertices_global_cm"] for facet in magnet["facets"]],
            dtype=np.float64)
        choices = []
        for facet in magnet["facets"]:
            center = np.asarray(facet["facet_centroid_global_cm"], dtype=np.float64)
            normal = np.asarray(facet["triangle_outward_normal_global"], dtype=np.float64)
            if abs(np.linalg.norm(normal) - 1.0) > 1.0e-10:
                raise ValueError("catalog outward normal is not unit length")
            if min(*(center[:2] - 0.2 * normal[:2]),
                   *(center[:2] + 0.2 * normal[:2])) > 0.5:
                choices.append(facet)
        if not choices:
            raise ValueError("no positive-quadrant interior facet for coil")
        facet = max(choices, key=lambda item: item["triangle_area_cm2"])
        center = np.asarray(facet["facet_centroid_global_cm"], dtype=np.float64)
        normal = np.asarray(facet["triangle_outward_normal_global"], dtype=np.float64)
        probes = []
        for offset in OFFSETS_CM:
            for side, expected in ((-1, "inside"), (1, "outside")):
                point = center + side * offset * normal
                ray_rows = []
                for direction in RAY_DIRECTIONS:
                    hits, margin, hit_distance = ray_hits(triangles, point, direction)
                    if (hits % 2 != (expected == "inside")
                            or margin < 1.0e-4 or hit_distance < 1.0e-6):
                        raise ValueError(f"mesh side/parity control failed: "
                                         f"volume {magnet['dagmc_volume_id']}")
                    smallest_bary_margin = min(smallest_bary_margin, margin)
                    smallest_hit_distance = min(smallest_hit_distance, hit_distance)
                    ray_rows.append({"hit_count": hits,
                                     "minimum_hit_barycentric_margin": margin,
                                     "nearest_hit_distance_cm": None if not np.isfinite(
                                         hit_distance) else hit_distance})
                probes.append({"side": expected, "offset_cm": offset,
                               "point_cm": point.tolist(), "rays": ray_rows})
        rows.append({"source_member": source_row["source_member"],
                     "dagmc_volume_id": magnet["dagmc_volume_id"],
                     "facet_id": facet["canonical_facet_id"],
                     "facet_index": facet["facet_index"],
                     "facet_area_cm2": facet["triangle_area_cm2"],
                     "facet_centroid_cm": center.tolist(),
                     "outward_normal": normal.tolist(),
                     "probes": probes})
    receipt = {
        "schema": "stellarcsg.p00-facet-side-bank/v1",
        "classification": "P00_ACCEPTED_MESH_FACET_SIDE_CONTROLS",
        "input_sha256": {"mapping": sha256(args.mapping),
                         "facet_catalog": sha256(catalog_path),
                         "dagmc_h5m": sha256(dagmc_path)},
        "coil_count": len(rows),
        "probe_count": sum(len(row["probes"]) for row in rows),
        "ray_check_count": sum(len(probe["rays"]) for row in rows
                               for probe in row["probes"]),
        "offsets_cm": list(OFFSETS_CM),
        "ray_directions": RAY_DIRECTIONS.tolist(),
        "minimum_hit_barycentric_margin": smallest_bary_margin,
        "minimum_positive_hit_distance_cm": smallest_hit_distance,
        "rows": rows,
        "claim_boundary": "The 108 probe points lie inside the positive x/y sector and pass three finite triangle-ray parity directions each against their hashed accepted-P00 facet-catalog group. These are finite mesh controls, not an independent readback of H5M triangles, a bound to continuous STEP CAD, a certified clearance envelope, or a StellarCSG root/transport pass.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"{receipt['classification']}: {receipt['probe_count']} probes, "
          f"{receipt['ray_check_count']} ray checks, min bary margin "
          f"{smallest_bary_margin:.8g}")


if __name__ == "__main__":
    main()
