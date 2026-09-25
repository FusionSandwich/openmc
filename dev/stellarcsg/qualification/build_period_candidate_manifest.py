"""Bind provisional one-period coil identities to the qualified HDF5 input.

Rotation families and sector admission are diagnostic inputs. This script
does not trim surfaces, assign periodic-plane ownership or create geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attribute_text(group: h5py.Group, name: str) -> str:
    value = group.attrs[name]
    return value.decode() if isinstance(value, bytes) else str(value)


def payload_content_id(group: h5py.Group) -> str:
    digest = hashlib.sha256(attribute_text(group, "canonical_metadata_json").encode())
    for name in ("centerline_coefficients", "normal_coefficients",
                 "binormal_coefficients", "major_radius_coefficients",
                 "minor_radius_coefficients"):
        digest.update(np.asarray(group[name], dtype="<f8", order="C").tobytes())
    return "sha256:" + digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--rotation-inventory", required=True, type=Path)
    parser.add_argument("--sector-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")

    h5_hash = sha256(args.h5)
    rotation_hash = sha256(args.rotation_inventory)
    rotation = json.loads(args.rotation_inventory.read_text())
    sector = json.loads(args.sector_inventory.read_text())
    if rotation["h5_sha256"] != h5_hash or sector["h5_sha256"] != h5_hash:
        raise ValueError("inventories refer to different HDF5 inputs")
    if sector["rotation_inventory_sha256"] != rotation_hash:
        raise ValueError("sector inventory does not bind the supplied rotation inventory")
    cycles = rotation["cycles"]
    if len(cycles) != 12 or any(not row["closes"] or len(row["members"]) != 4
                                for row in cycles):
        raise ValueError("expected twelve closed four-image cycles")
    rotation_rows = {row["member"]: row for row in rotation["rows"]}
    sector_rows = {row["member"]: row for row in sector["rows"]}
    members = [member for cycle in cycles for member in cycle["members"]]
    if len(set(members)) != 48 or set(members) != set(rotation_rows) \
            or set(members) != set(sector_rows):
        raise ValueError("inventories do not partition the same 48 members")
    if any(row["centerline_alignment"]["reverse"]
           or row["centerline_alignment"]["shift"] != 0
           for row in rotation_rows.values()):
        raise ValueError("nontrivial spline-index alignment requires explicit mapping")

    families = []
    rows = []
    with h5py.File(args.h5, "r") as handle:
        if set(handle["coils"]) != set(members):
            raise ValueError("coefficient file member set differs from inventories")
        for family, cycle in enumerate(cycles):
            selected = []
            for step, member in enumerate(cycle["members"]):
                rotated = cycle["members"][(step + 1) % 4]
                rotation_row = rotation_rows[member]
                sector_row = sector_rows[member]
                if rotation_row["rotated_match"] != rotated:
                    raise ValueError("rotation successor does not follow cycle")
                if sector_row["family"] != family \
                        or sector_row["image_step_from_cycle_start"] != step:
                    raise ValueError("sector member identity differs from rotation cycle")
                group = handle["coils"][member]
                coil_id = int(group.attrs["coil_id"])
                if member != f"coil_{coil_id:03d}":
                    raise ValueError("HDF5 coil_id and group name differ")
                if attribute_text(group, "units") != "cm" or \
                        attribute_text(group, "surface_type") != "swept-elliptical-cubic":
                    raise ValueError("unexpected coefficient payload schema")
                if len(group["centerline_coefficients"]) != sector_row["span_count"]:
                    raise ValueError("HDF5 control and sector span counts differ")
                content_id = attribute_text(group, "content_id")
                if content_id != payload_content_id(group):
                    raise ValueError("member canonical content ID does not match payload")
                admitted = sector_row["admitted_span_count"] > 0
                span_indices = sector_row["admitted_span_indices"]
                if len(span_indices) != sector_row["admitted_span_count"] \
                        or len(set(span_indices)) != len(span_indices) \
                        or any(index < 0 or index >= sector_row["span_count"]
                               for index in span_indices):
                    raise ValueError("invalid admitted span index list")
                if admitted:
                    selected.append(member)
                upper = sector_row["whole_surface_box_cm"][1]
                outside_margin = max(-float(upper[0]), -float(upper[1]))
                if not admitted and outside_margin <= 0.0:
                    raise ValueError("excluded member lacks whole-box separation")
                rows.append({
                    "member": member,
                    "coil_id": coil_id,
                    "dataset": f"/coils/{member}",
                    "content_id": content_id,
                    "rotational_family": family,
                    "family_canonical_member": cycle["members"][0],
                    "quarter_turns_from_canonical": step,
                    "sector_candidate": admitted,
                    "span_count": sector_row["span_count"],
                    "admitted_span_indices": span_indices,
                    "admitted_span_count": sector_row["admitted_span_count"],
                    "inside_box_span_count":
                        sector_row["inside_box_span_count"],
                    "touches_x_zero_box_count":
                        sector_row["touches_x_zero_box_count"],
                    "touches_y_zero_box_count":
                        sector_row["touches_y_zero_box_count"],
                    "outside_whole_box_margin_cm": outside_margin if not admitted
                    else None,
                    "rotation_to_successor_max_centerline_cm":
                        rotation_row["centerline_alignment"]["maximum_cm"],
                })
            families.append({
                "rotational_family": family,
                "canonical_member": cycle["members"][0],
                "full_device_members": cycle["members"],
                "sector_candidates": selected,
            })

    selected = [row for row in rows if row["sector_candidate"]]
    excluded = [row for row in rows if not row["sector_candidate"]]
    admitted_spans = sum(row["admitted_span_count"] for row in rows)
    if len(selected) != 18 or len(excluded) != 30 or admitted_spans != 3156:
        raise ValueError("frozen diagnostic sector admission changed")
    if any(not family["sector_candidates"] for family in families):
        raise ValueError("a rotational family has no sector candidate")
    # A deliberately large extra displacement test. It is evidence of ample
    # geometric separation for this diagnostic input, not a floating proof.
    stress_displacement_cm = 10.0
    minimum_margin = min(row["outside_whole_box_margin_cm"] for row in excluded)
    if minimum_margin <= stress_displacement_cm:
        raise ValueError("excluded member fails the 10 cm displacement stress")
    report = {
        "schema": "stellarcsg.period-candidate-manifest/v1",
        "input_hashes": {
            "h5_sha256": h5_hash,
            "rotation_inventory_sha256": rotation_hash,
            "sector_inventory_sha256": sha256(args.sector_inventory),
            "builder_sha256": sha256(Path(__file__)),
        },
        "field_period_degrees": 90,
        "full_device_member_count": len(rows),
        "rotational_family_count": len(families),
        "sector_candidate_count": len(selected),
        "sector_candidate_span_count": admitted_spans,
        "excluded_member_count": len(excluded),
        "minimum_excluded_whole_box_margin_cm": minimum_margin,
        "stress_extra_displacement_cm": stress_displacement_cm,
        "families": families,
        "members": rows,
        "claim_boundary": "Provisional rotation-family and sector candidate identities only. Approximate source rotations do not prove physical-coil identity, exact seam closure, floating bounds, winding-pack fidelity or transport. Whole periodic surfaces are not trimmed or assigned periodic-plane ownership.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "families": len(families),
        "sector_candidates": len(selected),
        "admitted_spans": admitted_spans,
        "excluded_members": len(excluded),
        "minimum_excluded_margin_cm": minimum_margin,
        "candidate_counts_by_family": [len(f["sector_candidates"]) for f in families],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
