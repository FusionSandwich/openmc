"""Independently compare a derived periodic facet candidate to accepted P00."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import h5py
import numpy as np


ACCEPTED_H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"
ACCEPTED_PAYLOAD_SHA256 = "126fdbec0a5795036ad75c7409f760652e47722d02f28fada89ddaf2fa71d9df"
ACCEPTED_RECEIPT_SHA256 = "acb484e5942dcd380c6fbbd741ab68df3f282c41cc6d7bf1170941abbb24b8ba"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(vertex: np.ndarray) -> tuple[float, float, float]:
    return tuple(0.0 if x == 0 else float(x) for x in vertex)


def read(path: Path):
    with h5py.File(path, "r") as handle:
        group = handle["facets/one_period"]
        vertices = np.asarray(group["triangle_vertices"], dtype="<f8")
        components = np.asarray(group["component_ids"], dtype="<i4")
        metadata = group.attrs["canonical_metadata_json"]
        identity = group.attrs["content_id"]
    if isinstance(metadata, bytes):
        metadata = metadata.decode()
    if isinstance(identity, bytes):
        identity = identity.decode()
    digest = hashlib.sha256(metadata.encode())
    digest.update(vertices.tobytes())
    digest.update(components.tobytes())
    if identity != "sha256:" + digest.hexdigest():
        raise ValueError(f"canonical content ID mismatch in {path}")
    return vertices, components, metadata, identity


def cap_keys(vertices: np.ndarray, axis: int) -> set:
    mask = np.max(np.abs(vertices[:, :, axis]), axis=1) <= 2.5e-13
    if np.count_nonzero(mask) != 80:
        raise ValueError("unexpected cap triangle count")
    projected = vertices[mask][:, :, [1, 2] if axis == 0 else [0, 2]]
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
    parser.add_argument("--candidate-payload", type=Path, required=True)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    accepted_receipt = json.loads(args.accepted_receipt.read_text())
    candidate_receipt = json.loads(args.candidate_receipt.read_text())
    if (sha256(args.accepted_receipt) != ACCEPTED_RECEIPT_SHA256
            or sha256(args.accepted_payload) != ACCEPTED_PAYLOAD_SHA256
            or accepted_receipt["input_sha256"]["accepted_h5m"]
            != ACCEPTED_H5M_SHA256
            or accepted_receipt["output_h5_sha256"] != sha256(args.accepted_payload)
            or candidate_receipt["output_h5_sha256"] != sha256(args.candidate_payload)
            or candidate_receipt["input_hashes"]["accepted_payload"]
            != sha256(args.accepted_payload)
            or candidate_receipt["input_hashes"]["accepted_receipt"]
            != sha256(args.accepted_receipt)
            or candidate_receipt["classification"]
            != "DERIVED_PERIODIC_CAP_CANDIDATE_NOT_ACCEPTED_H5M"):
        raise ValueError("payload and receipt ancestry differs")
    original, original_components, _, original_id = read(args.accepted_payload)
    candidate, candidate_components, metadata, candidate_id = read(
        args.candidate_payload)
    if (original.shape != candidate.shape or original.shape != (3348, 3, 3)
            or original_components.tobytes() != candidate_components.tobytes()
            or original_id != accepted_receipt["content_id"]
            or candidate_id != candidate_receipt["content_id"]):
        raise ValueError("triangle order, shape, IDs or content ID changed")
    canonical_metadata = json.loads(metadata)
    if (canonical_metadata["source_accepted_payload_sha256"]
            != sha256(args.accepted_payload)
            or canonical_metadata["source_accepted_content_id"] != original_id
            or canonical_metadata["accepted_h5m_sha256"]
            != accepted_receipt["input_sha256"]["accepted_h5m"]
            or candidate_receipt["accepted_h5m_sha256"]
            != ACCEPTED_H5M_SHA256):
        raise ValueError("candidate canonical metadata ancestry differs")
    accepted_cap_vertices = set()
    for axis in (0, 1):
        mask = np.max(np.abs(original[:, :, axis]), axis=1) <= 2.5e-13
        if np.count_nonzero(mask) != 80:
            raise ValueError("accepted cap topology differs")
        accepted_cap_vertices.update(key(vertex)
                                     for vertex in original[mask].reshape(-1, 3))
    changed = np.any(candidate.view("<u8") != original.view("<u8"), axis=2)
    changed_keys = {key(vertex) for vertex in original[changed]}
    if not changed_keys <= accepted_cap_vertices:
        raise ValueError("a non-cap accepted vertex moved")
    if len(changed_keys) != 180:
        raise ValueError("unexpected number of changed cap vertices")
    if cap_keys(candidate, 0) != cap_keys(candidate, 1):
        raise ValueError("candidate cap triangles are not bitwise periodic")
    displacement = np.linalg.norm(candidate - original, axis=2)
    maximum = float(np.max(displacement))
    upper = exact_displacement_upper(original, candidate)
    if (upper != candidate_receipt["maximum_displacement_outward_cm"]
            or upper != candidate_receipt["piecewise_linear_hausdorff_upper_cm"]
            or upper > 0.005):
        raise ValueError("candidate displacement receipt differs")
    receipt = {
        "schema": "stellarcsg.periodic-p00-facet-candidate-audit/v1",
        "state": "PASS_PERIODIC_CANDIDATE_MESH_COMPARISON",
        "triangle_count": 3348,
        "changed_distinct_cap_vertices": len(changed_keys),
        "changed_vertex_occurrences": int(np.count_nonzero(changed)),
        "maximum_vertex_displacement_cm": maximum,
        "piecewise_linear_hausdorff_upper_cm": upper,
        "rotated_cap_triangles_bitwise_equal": True,
        "hashes": {
            "auditor": sha256(Path(__file__)),
            "accepted_payload": sha256(args.accepted_payload),
            "accepted_receipt": sha256(args.accepted_receipt),
            "candidate_payload": sha256(args.candidate_payload),
            "candidate_receipt": sha256(args.candidate_receipt)},
        "claim_boundary": "Independent vertex-array comparison confirms identical triangle order and component IDs, movement only of the 180 original cap vertices, bitwise paired cap triangles and the stated maximum displacement. The same barycentric point on each pair of corresponding triangles differs by at most the maximum vertex displacement; therefore it bounds the piecewise-linear surface Hausdorff distance. This does not bound accepted-mesh error relative to continuous CAD or qualify histories."
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"],
                      "hausdorff_upper_cm": upper}))


if __name__ == "__main__":
    main()
