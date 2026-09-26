"""Inventory swept-coil spans that may touch the closed 0–90 degree sector.

Each periodic cubic centerline segment lies in the convex hull of its four
controls.  The C++ surface normalizes its transverse frame, so the maximum
positive radius control bounds the transverse displacement.  This produces
an intentionally broad per-span box; it is an admission diagnostic, not a
surface intersection or an ownership rule at either periodic plane.
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


def span_boxes(center: np.ndarray, major: np.ndarray,
               minor: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return outward-padded boxes from local periodic B-spline hulls."""
    if center.ndim != 2 or center.shape[1] != 3 or center.shape[0] < 4:
        raise ValueError("centerline controls must have shape (N>=4, 3)")
    n = center.shape[0]
    if major.shape != (n,) or minor.shape != (n,):
        raise ValueError("radius control counts differ from centerline")
    if not (np.isfinite(center).all() and np.isfinite(major).all()
            and np.isfinite(minor).all() and (major > 0).all()
            and (minor > 0).all()):
        raise ValueError("controls must be finite and radii positive")
    ids = (np.arange(n)[:, None] + np.arange(-1, 3)[None, :]) % n
    controls = center[ids]
    radius = np.maximum(major[ids].max(axis=1), minor[ids].max(axis=1))
    # Roundoff pad for an inventory only.  This is not a machine-checked
    # interval enclosure for the C++ evaluation path.
    scale = max(1.0, float(np.max(np.abs(center))), float(np.max(radius)))
    pad = 1.0e-10 * scale
    return controls.min(axis=1) - radius[:, None] - pad, \
        controls.max(axis=1) + radius[:, None] + pad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", required=True, type=Path)
    parser.add_argument("--rotation-inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    inventory = json.loads(args.rotation_inventory.read_text())
    if inventory["h5_sha256"] != sha256(args.h5):
        raise ValueError("rotation inventory is bound to a different HDF5")
    cycles = inventory["cycles"]
    if len(cycles) != 12 or any(not c["closes"] or len(c["members"]) != 4
                                for c in cycles):
        raise ValueError("expected twelve closed four-image cycles")
    members = [member for cycle in cycles for member in cycle["members"]]
    if len(set(members)) != 48:
        raise ValueError("rotation cycles do not partition 48 members")

    rows = []
    with h5py.File(args.h5, "r") as handle:
        if set(handle["coils"]) != set(members):
            raise ValueError("HDF5 member set differs from rotation inventory")
        for family, cycle in enumerate(cycles):
            for image, member in enumerate(cycle["members"]):
                group = handle["coils"][member]
                lower, upper = span_boxes(
                    np.asarray(group["centerline_coefficients"]),
                    np.asarray(group["major_radius_coefficients"]),
                    np.asarray(group["minor_radius_coefficients"]))
                admitted = (upper[:, 0] >= 0.0) & (upper[:, 1] >= 0.0)
                # A whole box within the closed quadrant does not prove
                # ownership of an exact boundary point.
                wholly_inside = ((lower[:, 0] >= 0.0) &
                                  (lower[:, 1] >= 0.0))
                rows.append({
                    "member": member, "family": family,
                    "image_step_from_cycle_start": image,
                    "span_count": int(len(lower)),
                    "admitted_span_indices": np.flatnonzero(admitted).tolist(),
                    "admitted_span_count": int(admitted.sum()),
                    "inside_box_span_count": int(wholly_inside.sum()),
                    "touches_x_zero_box_count": int(((lower[:, 0] <= 0.0) &
                                                      (upper[:, 0] >= 0.0)).sum()),
                    "touches_y_zero_box_count": int(((lower[:, 1] <= 0.0) &
                                                      (upper[:, 1] >= 0.0)).sum()),
                    "whole_surface_box_cm": [lower.min(axis=0).tolist(),
                                              upper.max(axis=0).tolist()],
                })
    report = {
        "schema": "stellarcsg.sector-span-inventory/v1",
        "h5_sha256": sha256(args.h5),
        "rotation_inventory_sha256": sha256(args.rotation_inventory),
        "sector": "closed first quadrant, 0 <= phi <= 90 degrees",
        "family_count": len(cycles),
        "rows": rows,
        "claim_boundary": "Per-span convex-hull boxes give broad admission only; floating evaluation enclosures, exact seam intersections, periodic ownership, winding-pack fidelity and transport remain unqualified.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "families": len(cycles),
        "admitted_members": sum(row["admitted_span_count"] > 0 for row in rows),
        "admitted_spans": sum(row["admitted_span_count"] for row in rows),
        "members_per_family": [sum(row["admitted_span_count"] > 0
                                   for row in rows if row["family"] == family)
                               for family in range(len(cycles))],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
