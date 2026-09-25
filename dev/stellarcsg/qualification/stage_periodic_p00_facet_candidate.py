"""Derive a periodic-cap candidate from the immutable accepted P00 facets.

Only matched vertices on the x=0 and y=0 cap meshes move. The output is a
new candidate with its own content ID, never a replacement for the accepted
H5M-derived payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import h5py
import numpy as np


DATASET = "/facets/one_period"
CAP_TOLERANCE_CM = 2.5e-13
ACCEPTED_H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"
ACCEPTED_PAYLOAD_SHA256 = "126fdbec0a5795036ad75c7409f760652e47722d02f28fada89ddaf2fa71d9df"
ACCEPTED_RECEIPT_SHA256 = "acb484e5942dcd380c6fbbd741ab68df3f282c41cc6d7bf1170941abbb24b8ba"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(metadata: str, vertices: np.ndarray,
                 components: np.ndarray) -> str:
    digest = hashlib.sha256(metadata.encode("utf-8"))
    digest.update(np.asarray(vertices, dtype="<f8", order="C").tobytes())
    digest.update(np.asarray(components, dtype="<i4", order="C").tobytes())
    return "sha256:" + digest.hexdigest()


def vertex_key(vertex: np.ndarray) -> tuple[float, float, float]:
    return tuple(0.0 if value == 0 else float(value) for value in vertex)


def bitwise_triangle_keys(projected: np.ndarray) -> set:
    bits = np.asarray(projected, dtype="<f8").view("<u8").reshape(-1, 3, 2)
    return {tuple(sorted(tuple(map(int, vertex)) for vertex in triangle))
            for triangle in bits}


def exact_displacement_upper(original: np.ndarray, candidate: np.ndarray) -> float:
    changed = np.argwhere(np.any(original != candidate, axis=2))
    largest_squared = Fraction(0)
    for triangle, vertex in changed:
        squared = sum((Fraction.from_float(float(candidate[triangle, vertex, axis]))
                       - Fraction.from_float(float(original[triangle, vertex, axis]))) ** 2
                      for axis in range(3))
        largest_squared = max(largest_squared, squared)
    upper = math.nextafter(math.sqrt(float(largest_squared)), math.inf)
    while Fraction.from_float(upper) ** 2 < largest_squared:
        upper = math.nextafter(upper, math.inf)
    return upper


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-payload", type=Path, required=True)
    parser.add_argument("--accepted-receipt", type=Path, required=True)
    parser.add_argument("--output-h5", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.output_h5.exists() or args.receipt.exists():
        parser.error("both outputs must be new")
    accepted = json.loads(args.accepted_receipt.read_text())
    if (accepted["schema"] != "stellarcsg.p00-facet-payload/v1"
            or sha256(args.accepted_receipt) != ACCEPTED_RECEIPT_SHA256
            or sha256(args.accepted_payload) != ACCEPTED_PAYLOAD_SHA256
            or accepted["input_sha256"]["accepted_h5m"] != ACCEPTED_H5M_SHA256
            or accepted["output_h5_sha256"] != sha256(args.accepted_payload)
            or accepted["triangle_count"] != 3348
            or accepted["component_ids"] != list(range(8, 26))):
        raise ValueError("accepted P00 payload differs from receipt")
    with h5py.File(args.accepted_payload, "r") as source:
        group = source[DATASET]
        if group.attrs["content_id"] != accepted["content_id"]:
            raise ValueError("accepted payload content ID differs")
        original = np.asarray(group["triangle_vertices"], dtype="<f8")
        components = np.asarray(group["component_ids"], dtype="<i4")
    if original.shape != (3348, 3, 3) or components.shape != (3348,):
        raise ValueError("accepted P00 shape differs")
    caps = [np.max(np.abs(original[:, :, axis]), axis=1)
            <= CAP_TOLERANCE_CM for axis in (0, 1)]
    if [int(np.count_nonzero(mask)) for mask in caps] != [80, 80]:
        raise ValueError("accepted periodic cap triangle counts differ")
    x_cap = original[caps[0]]
    y_cap = original[caps[1]]
    x_projected = x_cap[:, :, [1, 2]]
    y_projected = y_cap[:, :, [0, 2]]
    x_points = np.unique(x_projected.reshape(-1, 2), axis=0)
    y_points = np.unique(y_projected.reshape(-1, 2), axis=0)
    if x_points.shape != (90, 2) or y_points.shape != (90, 2):
        raise ValueError("accepted cap vertex counts differ")
    distances = np.linalg.norm(x_points[:, None, :] - y_points[None, :, :],
                               axis=2)
    x_to_y = np.argmin(distances, axis=1)
    y_to_x = np.argmin(distances, axis=0)
    if (len(set(map(int, x_to_y))) != 90
            or len(set(map(int, y_to_x))) != 90
            or not np.array_equal(y_to_x[x_to_y], np.arange(90))
            or float(np.max(distances[np.arange(90), x_to_y])) > 0.01):
        raise ValueError("cap vertices lack a unique close reciprocal match")
    x_lookup = {tuple(point): index for index, point in enumerate(x_points)}
    y_lookup = {tuple(point): index for index, point in enumerate(y_points)}
    x_topology = {tuple(sorted(x_lookup[tuple(point)] for point in triangle))
                  for triangle in x_projected}
    y_topology = {tuple(sorted(int(y_to_x[y_lookup[tuple(point)]])
                               for point in triangle))
                  for triangle in y_projected}
    if len(x_topology) != 80 or x_topology != y_topology:
        raise ValueError("paired cap triangle connectivity differs")

    replacements = {}
    for x_index, y_index in enumerate(x_to_y):
        x_point = x_points[x_index]
        y_point = y_points[y_index]
        common = 0.5 * (x_point + y_point)
        x_old = next(vertex for vertex in x_cap.reshape(-1, 3)
                     if np.array_equal(vertex[[1, 2]], x_point))
        y_old = next(vertex for vertex in y_cap.reshape(-1, 3)
                     if np.array_equal(vertex[[0, 2]], y_point))
        x_new = np.asarray((0.0, common[0], common[1]), dtype="<f8")
        y_new = np.asarray((common[0], 0.0, common[1]), dtype="<f8")
        for old, new in ((x_old, x_new), (y_old, y_new)):
            key = vertex_key(old)
            previous = replacements.setdefault(key, new)
            if not np.array_equal(previous, new):
                raise ValueError("one accepted vertex has conflicting replacements")
    candidate = original.copy()
    moved_occurrences = 0
    for triangle in candidate:
        for vertex in triangle:
            replacement = replacements.get(vertex_key(vertex))
            if replacement is not None:
                if not np.array_equal(vertex, replacement):
                    moved_occurrences += 1
                vertex[:] = replacement
    displacement = np.linalg.norm(candidate - original, axis=2)
    maximum = float(np.max(displacement))
    upper = exact_displacement_upper(original, candidate)
    if not np.isfinite(maximum) or maximum > 0.005:
        raise ValueError("periodic repair exceeds the 0.005 cm diagnostic cap")
    repaired_x = candidate[caps[0]][:, :, [1, 2]]
    repaired_y = candidate[caps[1]][:, :, [0, 2]]
    repaired_x_set = bitwise_triangle_keys(repaired_x)
    repaired_y_set = bitwise_triangle_keys(repaired_y)
    if repaired_x_set != repaired_y_set or len(repaired_x_set) != 80:
        raise ValueError("derived cap triangles are not bitwise periodic")
    metadata = json.dumps({
        "schema_version": [1, 0], "units": "cm",
        "triangle_count": 3348, "component_ids": list(range(8, 26)),
        "classification": "DERIVED_PERIODIC_CAP_CANDIDATE",
        "source_accepted_payload_sha256": sha256(args.accepted_payload),
        "source_accepted_content_id": accepted["content_id"],
        "accepted_h5m_sha256": accepted["input_sha256"]["accepted_h5m"],
        "transform": "mutual-nearest cap vertex bijection; shared binary64 midpoint",
    }, sort_keys=True, separators=(",", ":"))
    identity = canonical_id(metadata, candidate, components)
    args.output_h5.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.output_h5, "x") as output:
        group = output.create_group(DATASET)
        group.attrs["units"] = "cm"
        group.attrs["canonical_metadata_json"] = metadata
        group.attrs["content_id"] = identity
        group.create_dataset("triangle_vertices", data=candidate, dtype="<f8")
        group.create_dataset("component_ids", data=components, dtype="<i4")
    with h5py.File(args.output_h5, "r") as output:
        group = output[DATASET]
        stored = np.asarray(group["triangle_vertices"], dtype="<f8")
        stored_components = np.asarray(group["component_ids"], dtype="<i4")
        if (stored.tobytes() != candidate.tobytes()
                or stored_components.tobytes() != components.tobytes()
                or canonical_id(metadata, stored, stored_components) != identity):
            raise ValueError("derived payload readback changed")
    receipt = {
        "schema": "stellarcsg.periodic-p00-facet-candidate/v1",
        "classification": "DERIVED_PERIODIC_CAP_CANDIDATE_NOT_ACCEPTED_H5M",
        "dataset": DATASET, "content_id": identity,
        "triangle_count": 3348, "component_ids": list(range(8, 26)),
        "paired_cap_vertices": 90, "paired_cap_triangles": 80,
        "accepted_h5m_sha256": ACCEPTED_H5M_SHA256,
        "moved_vertex_occurrences": moved_occurrences,
        "maximum_accepted_vertex_displacement_cm": maximum,
        "maximum_displacement_outward_cm": upper,
        "piecewise_linear_hausdorff_upper_cm": upper,
        "input_hashes": {"accepted_payload": sha256(args.accepted_payload),
                         "accepted_receipt": sha256(args.accepted_receipt),
                         "transformer": sha256(Path(__file__))},
        "output_h5_sha256": sha256(args.output_h5),
        "claim_boundary": "The derived candidate keeps the accepted triangle connectivity and component IDs, moving only vertices on paired periodic caps. Corresponding piecewise-linear triangles differ pointwise by at most the maximum vertex displacement, which also bounds their set Hausdorff distance. The derived payload is not byte-identical to the accepted H5M and is not a continuous-CAD or transport certification."
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"classification": receipt["classification"],
                      "content_id": identity,
                      "hausdorff_upper_cm": upper}))


if __name__ == "__main__":
    main()
