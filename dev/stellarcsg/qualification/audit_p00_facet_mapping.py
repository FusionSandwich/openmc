"""Bind the accepted local P00 DAGMC coil facets to source-index candidates.

Bounding-box assignment is an identity diagnostic. It neither proves exact
CAD correspondence nor turns coarse DAGMC facets into a continuous surface.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p00-build", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--edge-receipt", required=True, type=Path)
    parser.add_argument("--edge-npz", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")

    dagmc = args.p00_build / "dagmc.h5m"
    catalog_path = args.p00_build / "magnet_boundary_facet_catalog.json"
    manifest_path = args.p00_build / "magnet_openmc_model_manifest.json"
    acceptance_path = args.p00_build / "geometry_acceptance_receipt.json"
    provenance = json.loads(args.provenance.read_text(encoding="utf-8"))
    edge_receipt = json.loads(args.edge_receipt.read_text(encoding="utf-8"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    hashes = {name: sha256(path) for name, path in {
        "dagmc_h5m": dagmc,
        "facet_catalog": catalog_path,
        "magnet_manifest": manifest_path,
        "acceptance_receipt": acceptance_path,
        "edge_receipt": args.edge_receipt,
        "edge_npz": args.edge_npz,
        "filament_provenance": args.provenance,
    }.items()}
    expected_coils = provenance["input_sha256"]["optimization_coils"]
    model = manifest["producer"]
    if (acceptance["status"] != "ACCEPTED"
            or hashes["acceptance_receipt"]
            != "3316b08887736e7f75cde613d112221360017b6dda494af96a4b993d64c910ed"
            or catalog["dagmc_file"]["sha256"] != hashes["dagmc_h5m"]
            or model["dagmc_file"]["sha256"] != hashes["dagmc_h5m"]
            or model["model_basis"]["input_sha256"]["coils.wistell-d"] != expected_coils
            or model["model_basis"]["parastell_case_sha256"]
            != provenance["p00_case_sha256"]
            or edge_receipt["input_sha256"]["coils"] != expected_coils
            or edge_receipt["input_sha256"]["provenance"]
            != hashes["filament_provenance"]
            or edge_receipt["output_npz_sha256"] != hashes["edge_npz"]):
        raise ValueError("P00 acceptance, input or edge-control identity mismatch")
    envelopes = model["envelopes"]
    magnets = catalog["magnets"]
    members = edge_receipt["members"]
    if (len(envelopes) != len(magnets) or len(magnets) != len(members)
            or len(magnets) != catalog["magnet_count"] or len(magnets) != 18
            or sum(row["facet_count"] for row in magnets) != catalog["facet_count"]
            or model["boundary_qa"]["closed_manifold"] is not True):
        raise ValueError("P00 coil collection count/topology declaration mismatch")

    source_boxes = []
    mesh_boxes = []
    with np.load(args.edge_npz) as archive:
        for row in members:
            points = np.asarray(archive[f"{row['member']}_edges_cm"], dtype=float)
            if points.shape != (4, 65, 3) or not np.isfinite(points).all():
                raise ValueError("invalid edge-control payload")
            points = points.reshape(-1, 3)
            source_boxes.append(np.stack((points.min(axis=0), points.max(axis=0))))
    for ordinal, (envelope, magnet) in enumerate(zip(envelopes, magnets), 1):
        expected_id = ordinal + 7
        if (envelope["dagmc_volume_id"] != magnet["dagmc_volume_id"]
                or envelope["dagmc_volume_id"] != expected_id
                or envelope["magnet_component"] != f"magnet-{ordinal:04d}"
                or len(magnet["facets"]) != magnet["facet_count"]):
            raise ValueError("magnet ordinal, volume or facet identity mismatch")
        points = np.asarray([
            facet["triangle_vertices_global_cm"] for facet in magnet["facets"]],
            dtype=float).reshape(-1, 3)
        if not np.isfinite(points).all():
            raise ValueError("nonfinite P00 facet vertex")
        mesh_boxes.append(np.stack((points.min(axis=0), points.max(axis=0))))
    source_boxes = np.asarray(source_boxes)
    mesh_boxes = np.asarray(mesh_boxes)
    cost = (np.linalg.norm(source_boxes[:, None, 0] - mesh_boxes[None, :, 0], axis=2)
            + np.linalg.norm(source_boxes[:, None, 1] - mesh_boxes[None, :, 1], axis=2))
    source_index, mesh_index = linear_sum_assignment(cost)
    if not np.array_equal(source_index, mesh_index):
        raise ValueError("minimum-cost source-to-facet assignment differs from ordinal mapping")
    baseline = float(cost[source_index, mesh_index].sum())
    alternative_margins = []
    for left, right in zip(source_index, mesh_index):
        forbidden = cost.copy()
        forbidden[left, right] = np.inf
        other_left, other_right = linear_sum_assignment(forbidden)
        alternative_margins.append(float(forbidden[other_left, other_right].sum() - baseline))
    if min(alternative_margins) <= 0.0:
        raise ValueError("bbox assignment is not uniquely minimum-cost")

    rows = []
    for index, (member, magnet) in enumerate(zip(members, magnets)):
        rows.append({
            "source_member": member["member"],
            "raw_filament_index": member["raw_filament_index"],
            "dagmc_volume_id": magnet["dagmc_volume_id"],
            "magnet_component": envelopes[index]["magnet_component"],
            "facet_count": magnet["facet_count"],
            "source_preclip_box_cm": source_boxes[index].tolist(),
            "accepted_mesh_box_cm": mesh_boxes[index].tolist(),
            "box_endpoint_distance_sum_cm": float(cost[index, index]),
            "forbid_this_pair_assignment_margin_cm": alternative_margins[index],
        })
    receipt = {
        "schema": "stellarcsg.p00-accepted-facet-mapping/v1",
        "classification": "ACCEPTED_P00_H5M_LOCAL_FACET_ORDER_DIAGNOSTIC",
        "input_sha256": hashes,
        "accepted_geometry_status": acceptance["status"],
        "accepted_receipt_manifest_sha256": acceptance["manifest"]["sha256"],
        "local_manifest_matches_accepted_receipt_hash": (
            hashes["magnet_manifest"] == acceptance["manifest"]["sha256"]),
        "accepted_dagmc_volume_ids": [row["dagmc_volume_id"] for row in magnets],
        "coil_count": len(magnets),
        "coil_facet_count": catalog["facet_count"],
        "bbox_assignment_cost_cm": baseline,
        "minimum_forbidden_pair_assignment_margin_cm": min(alternative_margins),
        "rows": rows,
        "claim_boundary": "The local H5M is byte-identical to accepted P00. A local facet catalog tied to that H5M and pre-CAD source-index order have a unique minimum-cost bbox assignment across 18 coil groups. The local magnet manifest does not match the accepted receipt's manifest hash, so this mapping is not an accepted-manifest identity claim. Large box differences for sector-clipped coils are expected. This diagnostic does not prove exact source-index-to-CAD identity, a continuous STEP-to-StellarCSG surface bound, collision-free CSG ownership or transport qualification.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"{receipt['classification']}: {len(rows)} coils, "
          f"{catalog['facet_count']} facets, minimum assignment margin "
          f"{min(alternative_margins):.6f} cm")


if __name__ == "__main__":
    main()
