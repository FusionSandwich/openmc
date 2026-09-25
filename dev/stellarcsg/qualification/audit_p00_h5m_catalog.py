"""Independently compare accepted P00 H5M triangles with its facet catalog.

Reads the MOAB H5M set, tag, connectivity and coordinate datasets through
h5py; does not call the catalog producer or PyMOAB.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sparse_int_tag(root: h5py.Group, name: str) -> dict[int, int]:
    tag = root[f"tags/{name}"]
    return {int(handle): int(value) for handle, value in
            zip(tag["id_list"][:], tag["values"][:], strict=True)}


def encoded_triangle(vertices: np.ndarray) -> bytes:
    if vertices.shape != (3, 3) or not np.isfinite(vertices).all():
        raise ValueError("invalid triangle coordinates")
    return struct.pack("<9d", *map(float, vertices.flat))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5m", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        parser.error("receipt must be a new path")
    h5m_hash = sha256(args.h5m)
    catalog_hash = sha256(args.catalog)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog["dagmc_file"]["sha256"] != h5m_hash:
        raise ValueError("catalog H5M hash mismatch")

    rows = []
    with h5py.File(args.h5m, "r") as file:
        sets = file["tstt/sets"]
        set_list = sets["list"][:]
        set_start = int(sets["list"].attrs["start_id"])
        global_ids = sets["tags/GLOBAL_ID"][:]
        if len(set_list) != len(global_ids) or set_list.shape[1] != 4:
            raise ValueError("unexpected MOAB set table layout")
        dimensions = sparse_int_tag(file["tstt"], "GEOM_DIMENSION")
        sense_tag = file["tstt/tags/GEOM_SENSE_2"]
        senses = {int(handle): tuple(map(int, pair)) for handle, pair in
                  zip(sense_tag["id_list"][:], sense_tag["values"][:], strict=True)}
        children = sets["children"][:]
        contents = sets["contents"][:]
        connectivity_ds = file["tstt/elements/Tri3/connectivity"]
        connectivity = connectivity_ds[:]
        triangle_start = int(connectivity_ds.attrs["start_id"])
        triangle_end = triangle_start + len(connectivity)
        coordinate_ds = file["tstt/nodes/coordinates"]
        coordinates = coordinate_ds[:]
        vertex_start = int(coordinate_ds.attrs["start_id"])
        volume_handles = {
            int(global_ids[index]): set_start + index
            for index in range(len(set_list))
            if dimensions.get(set_start + index) == 3
        }

        def set_row(handle: int) -> tuple[int, np.ndarray]:
            index = handle - set_start
            if not 0 <= index < len(set_list):
                raise ValueError(f"invalid MOAB set handle {handle}")
            return index, set_list[index]

        def child_sets(handle: int) -> list[int]:
            index, row = set_row(handle)
            start = int(set_list[index - 1, 1]) + 1 if index else 0
            return list(map(int, children[start:int(row[1]) + 1]))

        def triangle_handles(handle: int) -> list[int]:
            index, row = set_row(handle)
            start = int(set_list[index - 1, 0]) + 1 if index else 0
            data = contents[start:int(row[0]) + 1]
            flags = int(row[3])
            if flags == 10:  # MOAB range-compressed meshset: (first, count)
                if len(data) % 2:
                    raise ValueError("odd range-compressed meshset content")
                handles = [value for first, count in data.reshape(-1, 2)
                           for value in range(int(first), int(first + count))]
            elif flags == 2:  # MOAB unordered meshset: explicit handles
                handles = list(map(int, data))
            else:
                raise ValueError(f"unexpected MOAB meshset flags {flags}")
            return [value for value in handles
                    if triangle_start <= value < triangle_end]

        for magnet in catalog["magnets"]:
            volume_id = int(magnet["dagmc_volume_id"])
            volume = volume_handles[volume_id]
            surface_handles = [handle for handle in child_sets(volume)
                               if dimensions.get(handle) == 2]
            surface_ids = {int(global_ids[handle - set_start])
                           for handle in surface_handles}
            if surface_ids != set(magnet["surface_ids"]):
                raise ValueError(f"volume {volume_id} surface IDs mismatch")
            observed: Counter[tuple[int, bytes]] = Counter()
            for surface in surface_handles:
                surface_id = int(global_ids[surface - set_start])
                sense = senses[surface]
                if sense[0] == volume:
                    sign = 1
                elif sense[1] == volume:
                    sign = -1
                else:
                    raise ValueError(f"surface {surface_id} lacks volume sense")
                for handle in triangle_handles(surface):
                    node_handles = connectivity[handle - triangle_start].astype(np.int64)
                    vertices = coordinates[node_handles - vertex_start]
                    if sign == -1:
                        vertices = vertices[[0, 2, 1]]
                    observed[(surface_id, encoded_triangle(vertices))] += 1
            expected: Counter[tuple[int, bytes]] = Counter(
                (int(facet["surface_id"]),
                 encoded_triangle(np.asarray(facet["triangle_vertices_global_cm"],
                                             dtype=np.float64)))
                for facet in magnet["facets"])
            if observed != expected:
                missing = sum((expected - observed).values())
                extra = sum((observed - expected).values())
                raise ValueError(f"volume {volume_id}: {missing} missing, {extra} extra triangles")
            rows.append({"volume_id": volume_id,
                         "surface_count": len(surface_ids),
                         "triangle_count": sum(observed.values()),
                         "bitwise_oriented_triangle_multiset_match": True})

    if len(rows) != catalog["magnet_count"] or sum(
            row["triangle_count"] for row in rows) != catalog["facet_count"]:
        raise ValueError("catalog component or facet count mismatch")
    receipt = {
        "schema": "stellarcsg.p00-h5m-catalog-readback/v1",
        "classification": "DIRECT_H5M_ORIENTED_TRIANGLE_MATCH",
        "claim_boundary": "Independent h5py readback of the 18 accepted P00 magnet volumes and their oriented triangle multisets against the catalog. This does not certify continuous CAD, sector ownership, or StellarCSG transport.",
        "h5m_sha256": h5m_hash,
        "catalog_sha256": catalog_hash,
        "magnet_count": len(rows),
        "facet_count": sum(row["triangle_count"] for row in rows),
        "rows": rows,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_bytes((json.dumps(receipt, indent=2, sort_keys=True)
                              + "\n").encode("utf-8"))
    print(json.dumps({key: receipt[key] for key in (
        "classification", "h5m_sha256", "catalog_sha256",
        "magnet_count", "facet_count")}))


if __name__ == "__main__":
    main()
