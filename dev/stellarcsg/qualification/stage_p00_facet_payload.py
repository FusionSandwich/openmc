"""Stage the accepted P00 one-period triangle set in a portable HDF5 payload.

The input fixture is already bound to the accepted H5M by its receipt and an
independent oriented-triangle readback. This converter preserves every stored
binary64 vertex and the DAGMC volume ID assigned to each triangle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def content_id(metadata: str, vertices: np.ndarray, components: np.ndarray) -> str:
    digest = hashlib.sha256(metadata.encode("utf-8"))
    digest.update(np.asarray(vertices, dtype="<f8", order="C").tobytes())
    digest.update(np.asarray(components, dtype="<i4", order="C").tobytes())
    return "sha256:" + digest.hexdigest()


def as_text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--fixture-receipt", required=True, type=Path)
    parser.add_argument("--output-h5", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.output_h5.exists() or args.receipt.exists():
        parser.error("output HDF5 and receipt must both be new")

    fixture_hash = sha256(args.fixture)
    fixture_receipt_hash = sha256(args.fixture_receipt)
    fixture_receipt = json.loads(args.fixture_receipt.read_text())
    if (fixture_receipt["schema"] != "stellarcsg.p00-facet-fixture/v1"
            or fixture_receipt["fixture_sha256"] != fixture_hash
            or fixture_receipt["facet_count"] != 3348
            or fixture_receipt["probe_count"] != 108):
        raise ValueError("fixture differs from its accepted-P00 receipt")

    lines = args.fixture.read_text(encoding="ascii").splitlines()
    triangle_count = int(lines[0])
    if triangle_count != fixture_receipt["facet_count"]:
        raise ValueError("unexpected triangle count")
    vertices = np.empty((triangle_count, 3, 3), dtype="<f8")
    components = np.empty(triangle_count, dtype="<i4")
    for index, line in enumerate(lines[1:triangle_count + 1]):
        tokens = line.split()
        if len(tokens) != 10:
            raise ValueError(f"triangle {index} does not have 10 fields")
        component = int(tokens[0])
        if not 0 < component <= np.iinfo(np.int32).max:
            raise ValueError(f"triangle {index} has invalid component ID")
        components[index] = component
        vertices[index] = np.asarray([float(value) for value in tokens[1:]],
                                     dtype="<f8").reshape(3, 3)
    if not np.isfinite(vertices).all():
        raise ValueError("nonfinite triangle vertex")
    if len(lines) != triangle_count + 2 + fixture_receipt["probe_count"]:
        raise ValueError("fixture length differs from header")
    if int(lines[triangle_count + 1]) != fixture_receipt["probe_count"]:
        raise ValueError("probe header differs from receipt")
    # The probe suffix is evidence in the fixture, not part of the surface.
    if any(len(line.split()) != 5 for line in lines[triangle_count + 2:]):
        raise ValueError("malformed probe suffix")
    ids = sorted(set(map(int, components)))
    if ids != list(range(8, 26)):
        raise ValueError("accepted P00 DAGMC volume IDs differ")

    metadata = json.dumps({
        "schema_version": [1, 0], "units": "cm",
        "triangle_count": triangle_count,
        "component_ids": ids,
        "source_fixture_sha256": fixture_hash,
        "accepted_h5m_sha256": fixture_receipt["h5m_sha256"],
    }, sort_keys=True, separators=(",", ":"))
    identity = content_id(metadata, vertices, components)
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.output_h5, "x") as h5:
        group = h5.create_group("facets/one_period")
        group.attrs["units"] = "cm"
        group.attrs["canonical_metadata_json"] = metadata
        group.attrs["content_id"] = identity
        group.create_dataset("triangle_vertices", data=vertices, dtype="<f8")
        group.create_dataset("component_ids", data=components, dtype="<i4")

    # Reopen the exact file that the native adapter will consume.
    with h5py.File(args.output_h5, "r") as h5:
        group = h5["facets/one_period"]
        stored_vertices = np.asarray(group["triangle_vertices"], dtype="<f8")
        stored_components = np.asarray(group["component_ids"], dtype="<i4")
        if (group.attrs["units"] != "cm"
                or as_text(group.attrs["canonical_metadata_json"]) != metadata
                or as_text(group.attrs["content_id"]) != identity
                or stored_vertices.tobytes() != vertices.tobytes()
                or stored_components.tobytes() != components.tobytes()
                or content_id(metadata, stored_vertices, stored_components) != identity):
            raise ValueError("written facet payload differs from fixture")

    receipt = {
        "schema": "stellarcsg.p00-facet-payload/v1",
        "classification": "ACCEPTED_P00_TRIANGLES_PRESERVED_IN_HDF5",
        "dataset": "/facets/one_period",
        "content_id": identity,
        "triangle_count": triangle_count,
        "component_ids": ids,
        "input_sha256": {
            "fixture": fixture_hash,
            "fixture_receipt": fixture_receipt_hash,
            "accepted_h5m": fixture_receipt["h5m_sha256"],
            "converter": sha256(Path(__file__)),
        },
        "output_h5_sha256": sha256(args.output_h5),
        "claim_boundary": "Stored HDF5 triangles and component IDs reproduce the accepted P00 fixture exactly after readback, with a canonical payload ID. The payload is the accepted faceted approximation, not a continuous CAD or native transport certification."
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in
                      ("classification", "triangle_count", "content_id")}))


if __name__ == "__main__":
    main()
