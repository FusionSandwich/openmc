"""Stage a provisional 90-degree swept-coil region with paired planes.

The cells are deliberately unfilled: this checks geometry ownership and XML
identity before any physical magnet material or transport is admitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import openmc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--period-box-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != (repo / "openmc/__init__.py").resolve():
        raise ValueError("not using this OpenMC checkout")
    manifest = json.loads(args.manifest.read_text())
    bound = json.loads(args.period_box_receipt.read_text())
    input_hash = sha256(args.h5)
    if (manifest["input_hashes"]["h5_sha256"] != input_hash
            or bound["sha256"]["candidate_h5"] != input_hash
            or bound["state"] != "PROVISIONAL_PERIOD_PYTHON_BOUNDS_FINITE"):
        raise ValueError("candidate identity and bounding box do not match")
    selected = [row for row in manifest["members"] if row["sector_candidate"]]
    ids = bound["selected_member_ids"]
    if (len(ids) != 18 or len(set(ids)) != 18
            or set(ids) != {row["coil_id"] for row in selected}):
        raise ValueError("candidate selected-set identity differs")
    content_by_coil = {row["coil_id"]: row["content_id"] for row in selected}
    member_content_ids = [content_by_coil[coil_id] for coil_id in ids]
    with h5py.File(args.h5) as h5:
        for row in selected:
            stored = h5[row["dataset"]].attrs["content_id"]
            if isinstance(stored, bytes):
                stored = stored.decode()
            if stored != row["content_id"]:
                raise ValueError("selected coefficient content ID differs")

    radial_limit = 2500.0
    axial_limit = 700.0
    lower, upper = bound["box_lower_cm"], bound["box_upper_cm"]
    if (math.hypot(max(map(abs, (lower[0], upper[0]))),
                   max(map(abs, (lower[1], upper[1])))) >= radial_limit
            or max(abs(lower[2]), abs(upper[2])) >= axial_limit):
        raise ValueError("provisional outer enclosure would clip a coil box")

    openmc.reset_auto_ids()
    x0 = openmc.XPlane(0.0, boundary_type="periodic", surface_id=901)
    y0 = openmc.YPlane(0.0, boundary_type="periodic", surface_id=902)
    x0.periodic_surface = y0
    coils = openmc.SweptSplineSurface(
        args.h5.resolve(), dataset_prefix="/coils/coil_",
        dataset_indices=ids, member_content_ids=member_content_ids,
        surface_id=903)
    radial = openmc.ZCylinder(r=radial_limit, boundary_type="vacuum",
                              surface_id=904)
    zmin = openmc.ZPlane(-axial_limit, boundary_type="vacuum", surface_id=905)
    zmax = openmc.ZPlane(axial_limit, boundary_type="vacuum", surface_id=906)
    sector = +x0 & +y0 & -radial & +zmin & -zmax
    coil_cell = openmc.Cell(cell_id=1001, name="provisional-coil-region",
                            region=sector & -coils)
    complement_cell = openmc.Cell(cell_id=1002, name="provisional-complement",
                                  region=sector & +coils)
    args.output.mkdir(parents=True)
    xml_path = args.output / "geometry.xml"
    openmc.Geometry([coil_cell, complement_cell]).export_to_xml(path=xml_path)
    openmc.reset_auto_ids()
    reloaded = openmc.Geometry.from_xml(path=xml_path, materials=openmc.Materials())
    cells = reloaded.get_all_cells()
    surfaces = reloaded.get_all_surfaces()
    if (set(cells) != {1001, 1002} or set(surfaces) != set(range(901, 907))
            or surfaces[901].periodic_surface is not surfaces[902]
            or surfaces[902].periodic_surface is not surfaces[901]
            or not surfaces[903].is_equal(coils)
            or str(cells[1001].region) != str(coil_cell.region)
            or str(cells[1002].region) != str(complement_cell.region)
            or cells[1001].fill is not None or cells[1002].fill is not None):
        raise ValueError("one-period Python XML roundtrip changed ownership")
    # This tests the plane-side contract independently of the native swept
    # evaluator, which remains unavailable to Python point classification.
    for point, expected in (((1, 1, 0), True), ((-1, 1, 0), False),
                            ((1, -1, 0), False)):
        if (point in (+surfaces[901] & +surfaces[902])) != expected:
            raise ValueError("period plane side changed")
    receipt = {
        "schema": "stellarcsg.provisional-period-region/v1",
        "state": "PROVISIONAL_SECTOR_XML_ROUNDTRIP_ONLY",
        "field_period_degrees": 90,
        "selected_member_ids": ids,
        "selected_member_content_ids": member_content_ids,
        "sector_halfspaces": ["x>=0", "y>=0"],
        "periodic_plane_ids": [901, 902],
        "coil_surface_id": 903,
        "coil_cell_id": 1001,
        "complement_cell_id": 1002,
        "registered_whole_coil_span_count": bound["registered_whole_coil_span_count"],
        "manifest_admitted_span_count": bound["manifest_admitted_span_count"],
        "radial_outer_vacuum_cm": radial_limit,
        "axial_outer_vacuum_cm": axial_limit,
        "hashes": {"builder": sha256(Path(__file__)), "h5": input_hash,
                   "manifest": sha256(args.manifest),
                   "period_box_receipt": sha256(args.period_box_receipt),
                   "geometry_xml": sha256(xml_path)},
        "claim_boundary": "Python XML records two complementary unfilled cells inside paired x=0/y=0 periodic planes. Full coil surfaces are clipped by region intersection for material ownership, without removing their unadmitted spans from native evaluation. The physical winding pack, native periodic-plane handling, root completeness, source clearance, material assignment and transport remain unqualified."
    }
    (args.output / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"], len(ids))


if __name__ == "__main__":
    main()
