"""Use exact stored-power hulls to test P00 mesh probes against the ellipse.

The real cardinal cubic B-spline lies in each four-control convex hull. An
inward P00 mesh probe farther than the maximum ellipse radius from every
padded centerline hull cannot lie in the represented elliptical tube.
"""

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


PAD_CM = Fraction(1, 1_000_000)
MAX_RADIUS_CM = Fraction(10)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def span_boxes_exact(controls: np.ndarray) -> list[tuple[tuple[Fraction, ...],
                                                       tuple[Fraction, ...]]]:
    exact = [[Fraction.from_float(float(value)) for value in row]
             for row in controls]
    count = len(exact)
    return [
        (tuple(min(exact[j][axis] for j in indices) - PAD_CM
               for axis in range(3)),
         tuple(max(exact[j][axis] for j in indices) + PAD_CM
               for axis in range(3)))
        for index in range(count)
        for indices in [[(index + offset) % count for offset in (-1, 0, 1, 2)]]
    ]


def min_box_gap_squared(point: list[float], boxes: list) -> Fraction:
    coordinates = [Fraction.from_float(value) for value in point]
    squared = []
    for lower, upper in boxes:
        gaps = [max(lower[axis] - coordinates[axis],
                    coordinates[axis] - upper[axis], Fraction(0))
                for axis in range(3)]
        squared.append(sum(gap * gap for gap in gaps))
    return min(squared)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--candidate-h5", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    bank = json.loads(args.bank.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if (bank["classification"] != "P00_ACCEPTED_MESH_FACET_SIDE_CONTROLS"
            or manifest["input_hashes"]["h5_sha256"] != sha256(args.candidate_h5)
            or manifest["sector_candidate_count"] != 18
            or len(bank["rows"]) != 18):
        raise ValueError("P00 facet bank or elliptical candidate identity mismatch")
    admitted = {row["member"] for row in manifest["members"]
                if row["sector_candidate"]}
    if admitted != {row["source_member"] for row in bank["rows"]}:
        raise ValueError("P00 facet bank member set differs from ellipse manifest")
    basis_source = Path(__file__).resolve().parents[1] / "python/stellarcsg/spline.py"
    basis_text = basis_source.read_text(encoding="utf-8")
    if "(cell + offset - 1) % coeff.size" not in basis_text:
        raise ValueError("cardinal cubic control indexing changed")

    rows = []
    with h5py.File(args.candidate_h5, "r") as handle:
        for bank_row in bank["rows"]:
            member = bank_row["source_member"]
            group = handle["coils"][member]
            center = np.asarray(group["centerline_coefficients"], dtype=np.float64)
            major = np.asarray(group["major_radius_coefficients"], dtype=np.float64)
            minor = np.asarray(group["minor_radius_coefficients"], dtype=np.float64)
            if (center.shape != (256, 3) or not np.isfinite(center).all()
                    or not np.all(major == 10.0) or not np.all(minor == 8.0)):
                raise ValueError(f"ellipse controls changed for {member}")
            boxes = span_boxes_exact(center)
            probes = []
            for probe in bank_row["probes"]:
                if probe["side"] != "inside":
                    continue
                minimum = min_box_gap_squared(probe["point_cm"], boxes)
                beyond = minimum > MAX_RADIUS_CM**2
                probes.append({
                    "offset_cm": probe["offset_cm"],
                    "exact_minimum_box_gap_squared_gt_radius_squared": beyond,
                    "minimum_box_gap_cm_approx": float(minimum) ** 0.5,
                    "box_gap_squared_excess_cm2_approx": float(
                        minimum - MAX_RADIUS_CM**2),
                })
            if len(probes) != 3 or {probe["offset_cm"] for probe in probes} != {
                    0.05, 0.1, 0.2}:
                raise ValueError(f"incomplete inward-probe bank for {member}")
            rows.append({"source_member": member,
                         "dagmc_volume_id": bank_row["dagmc_volume_id"],
                         "inside_probes": probes,
                         "all_three_probes_beyond_ellipse": all(
                             probe["exact_minimum_box_gap_squared_gt_radius_squared"]
                             for probe in probes)})
    excluded = [row["source_member"] for row in rows
                if row["all_three_probes_beyond_ellipse"]]
    receipt = {
        "schema": "stellarcsg.p00-ellipse-mismatch/v1",
        "classification": "FINITE_P00_MESH_INSIDE_PROBES_OUTSIDE_REAL_ELLIPSE",
        "input_sha256": {"facet_side_bank": sha256(args.bank),
                         "ellipse_candidate_h5": sha256(args.candidate_h5),
                         "ellipse_manifest": sha256(args.manifest),
                         "cardinal_cubic_basis_source": sha256(basis_source)},
        "maximum_ellipse_radius_cm": float(MAX_RADIUS_CM),
        "exact_rational_box_pad_cm": str(PAD_CM),
        "real_spline_property": "Each periodic cubic span lies in the convex hull of its four stored binary64 controls, interpreted as exact real values.",
        "mesh_inside_probe_count": sum(len(row["inside_probes"]) for row in rows),
        "probes_proved_beyond_ellipse": sum(
            probe["exact_minimum_box_gap_squared_gt_radius_squared"]
            for row in rows for probe in row["inside_probes"]),
        "coil_count_with_three_proved_mismatches": len(excluded),
        "coil_members_with_three_proved_mismatches": excluded,
        "rows": rows,
        "claim_boundary": "Exact rational comparison proves the named stored-binary64 P00 mesh probe coordinates are farther than 10 cm from every padded real B-spline centerline span for the named diagnostic ellipse. The inside labels come from finite parity checks of the local facet catalog tied by hash to accepted P00 H5M. This is a decisive sampled geometry mismatch, not a continuous CAD tolerance bound, a machine enclosure of the compiled floating evaluator, or a transport result. A negative/inconclusive box result does not establish agreement.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"{receipt['classification']}: "
          f"{receipt['probes_proved_beyond_ellipse']}/"
          f"{receipt['mesh_inside_probe_count']} probes, "
          f"{len(excluded)}/18 coils")


if __name__ == "__main__":
    main()
