"""Extract source-bound ParaStell P00 rectangular coil edge control points.

The output reproduces numerical pre-CAD sampling and offsets from the audited
local ParaStell recipe. CadQuery splines, ruled faces, clipping and STEP solids
are outside this extract's claim.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_filaments(path: Path) -> list[np.ndarray]:
    """Match ParaStell's MAKEGRID float parsing, scale and explicit closure."""
    data = path.read_text(encoding="utf-8").splitlines()[3:]
    filaments = []
    coords = []
    for line in data:
        columns = line.strip().split()
        if not columns:
            continue
        if columns[0] == "end":
            break
        if float(columns[3]) != 0.0:
            coords.append([float(value) * 100.0 for value in columns[:3]])
        else:
            coords.append(coords[0])
            filaments.append(np.asarray(coords, dtype=np.float64))
            coords = []
    if coords or len(filaments) != 48:
        raise ValueError("expected 48 complete WISTELL-D filaments")
    return filaments


def tangent_at_raw_points(coords: np.ndarray) -> np.ndarray:
    forward = np.append(coords[1:], [coords[1]], axis=0)
    backward = np.append([coords[-2]], coords[:-1], axis=0)
    tangent = forward - backward
    return tangent / np.linalg.norm(tangent, axis=1)[:, None]


def candidate_indices(filaments: list[np.ndarray], width: float,
                      thickness: float, extent_deg: float) -> tuple[list[int], float]:
    unique_points = [coords[:-1] for coords in filaments]
    radii_count = sum(len(points) for points in unique_points)
    average_radius = sum(np.linalg.norm(points[:, :2], axis=1).sum()
                         for points in unique_points) / radii_count
    tol = 2.0 * np.arctan2(max(width, thickness), average_radius)
    lower = 2.0 * np.pi - tol
    upper = np.deg2rad(extent_deg) + tol
    selected = []
    for index, coords in enumerate(filaments):
        angles = (np.arctan2(coords[:, 1], coords[:, 0]) + 2.0 * np.pi) % (2.0 * np.pi)
        if (angles.min() >= lower or angles.min() <= upper or
                angles.max() >= lower or angles.max() <= upper):
            selected.append(index)
    selected.sort(key=lambda index: float(np.arctan2(
        filaments[index][:-1, 1].mean(), filaments[index][:-1, 0].mean())))
    return selected, float(tol)


def edge_controls(coords: np.ndarray, sample_mod: int, width: float,
                  thickness: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sampled_coords = np.append(coords[0:-1:sample_mod], [coords[0]], axis=0)
    tangent = tangent_at_raw_points(coords)
    sampled_tangent = np.append(tangent[0:-1:sample_mod], [tangent[0]], axis=0)
    center_of_mass = coords[:-1].mean(axis=0)
    outward = sampled_coords - center_of_mass
    outward /= np.linalg.norm(outward, axis=1)[:, None]
    parallel = np.einsum("ij,ij->i", outward, sampled_tangent)
    normal = outward - parallel[:, None] * sampled_tangent
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    binormal = np.cross(sampled_tangent, normal)
    offsets = ((-1, -1), (-1, 1), (1, 1), (1, -1))
    edges = np.stack([
        sampled_coords + side * binormal * (width / 2.0)
        + radial * normal * (thickness / 2.0)
        for side, radial in offsets])
    return edges, sampled_tangent, sampled_coords


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--coils", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-npz", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    if args.output_npz.exists() or args.receipt.exists():
        parser.error("both outputs must be new")
    provenance = json.loads(args.provenance.read_text(encoding="utf-8"))
    if (provenance["classification"]
            != "NOMINAL_P00_SECTION_SOURCE_IDENTIFIED_CAD_UNVERIFIED"
            or sha256(args.coils) != provenance["input_sha256"]["optimization_coils"]):
        raise ValueError("filament or provenance identity mismatch")
    parastell_source = (Path(provenance["source_paths"]["local_parastell_root"])
                        / "parastell/magnet_coils.py")
    p00_config = (Path(provenance["source_paths"]["p00_case_dir"])
                  / "parastell_config.yaml")
    if (sha256(parastell_source)
            != provenance["input_sha256"]["local_parastell_magnet_coils"]
            or sha256(p00_config) != provenance["input_sha256"]["p00_config"]):
        raise ValueError("ParaStell recipe or P00 configuration changed")
    params = provenance["p00_magnet_coils"]
    width, thickness = float(params["width_cm"]), float(params["thickness_cm"])
    sample_mod = int(params["sample_mod"])
    extent = float(params["toroidal_extent_deg"])
    if (width, thickness, sample_mod, extent) != (30.0, 30.0, 6, 90.0):
        raise ValueError("P00 recipe changed; review extraction")
    filaments = read_filaments(args.coils)
    selected, tolerance = candidate_indices(filaments, width, thickness, extent)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["full_device_member_count"] != 48:
        raise ValueError("manifest full-device identity mismatch")
    provisional = {row["member"] for row in manifest["members"]
                   if row["sector_candidate"]}
    selected_members = {f"coil_{1000 + index}" for index in selected}
    if len(selected) != 18 or selected_members != provisional:
        raise ValueError("ParaStell pre-CAD candidates differ from the 18-member sector inventory")

    arrays = {}
    rows = []
    for index in selected:
        member = f"coil_{1000 + index}"
        edges, tangents, centers = edge_controls(
            filaments[index], sample_mod, width, thickness)
        if not np.isfinite(edges).all() or not np.isfinite(tangents).all():
            raise ValueError(f"nonfinite edge controls for {member}")
        if not np.array_equal(edges[:, 0], edges[:, -1]):
            raise ValueError(f"edge-control loop does not close for {member}")
        side_lengths = np.linalg.norm(np.roll(edges, -1, axis=0) - edges, axis=2)
        side_targets = np.asarray([thickness, width, thickness, width])[:, None]
        max_side_error = float(np.max(np.abs(side_lengths - side_targets)))
        max_center_error = float(np.max(np.linalg.norm(
            edges.mean(axis=0) - centers, axis=1)))
        max_tangent_edge_dot = float(np.max(np.abs(np.einsum(
            "ijk,jk->ij", edges - centers[None, :, :], tangents))))
        if max(max_side_error, max_center_error, max_tangent_edge_dot) > 1.0e-9:
            raise ValueError(f"rectangular section geometry failed for {member}")
        arrays[f"{member}_edges_cm"] = edges
        arrays[f"{member}_tangents"] = tangents
        rows.append({"member": member, "raw_filament_index": index,
                     "edge_control_shape": list(edges.shape),
                     "max_side_length_error_cm": max_side_error,
                     "max_corner_mean_to_center_error_cm": max_center_error,
                     "max_tangent_to_corner_offset_dot_cm": max_tangent_edge_dot,
                     "coordinate_min_cm": edges.min(axis=(0, 1)).tolist(),
                     "coordinate_max_cm": edges.max(axis=(0, 1)).tolist()})
    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output_npz, **arrays)
    receipt = {
        "schema": "stellarcsg.p00-edge-controls/v1",
        "classification": "PARASTELL_NUMERICAL_PRE_CAD_CONTROLS",
        "input_sha256": {"coils": sha256(args.coils),
                         "provenance": sha256(args.provenance),
                         "provisional_ellipse_manifest": sha256(args.manifest)},
        "output_npz_sha256": sha256(args.output_npz),
        "width_cm": width, "thickness_cm": thickness,
        "sample_mod": sample_mod, "toroidal_extent_deg": extent,
        "prefilter_tolerance_rad": tolerance,
        "raw_filament_count": len(filaments),
        "pre_cad_candidate_count": len(selected),
        "provisional_ellipse_candidate_count": len(provisional),
        "pre_cad_only_members": sorted(selected_members - provisional),
        "provisional_ellipse_only_members": sorted(provisional - selected_members),
        "members": rows,
        "claim_boundary": "Numerical samples before CadQuery spline interpolation, ruled faces, sector intersection, zero-volume filtering, and STEP export. These controls are neither a complete physical surface nor a transport-qualified StellarCSG payload.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in (
        "classification", "pre_cad_candidate_count",
        "provisional_ellipse_candidate_count", "pre_cad_only_members",
        "provisional_ellipse_only_members")}))


if __name__ == "__main__":
    main()
