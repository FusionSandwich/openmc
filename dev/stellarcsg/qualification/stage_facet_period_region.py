"""Stage an unfilled 90-degree CSG region from a bound P00 facet payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import openmc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--payload-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != (repo / "openmc/__init__.py").resolve():
        raise ValueError("not using this OpenMC checkout")
    source = json.loads(args.payload_receipt.read_text())
    accepted = source["schema"] == "stellarcsg.p00-facet-payload/v1"
    derived = source["schema"] == "stellarcsg.periodic-p00-facet-candidate/v1"
    if (not (accepted or derived)
            or source["output_h5_sha256"] != sha256(args.payload)
            or source["triangle_count"] != 3348
            or source["component_ids"] != list(range(8, 26))):
        raise ValueError("P00 facet payload identity differs")
    if derived and source["classification"] != \
            "DERIVED_PERIODIC_CAP_CANDIDATE_NOT_ACCEPTED_H5M":
        raise ValueError("derived facet classification differs")
    identity = source["content_id"]
    openmc.reset_auto_ids()
    x0 = openmc.XPlane(0.0, boundary_type="periodic", surface_id=901)
    y0 = openmc.YPlane(0.0, boundary_type="periodic", surface_id=902)
    x0.periodic_surface = y0
    coils = openmc.FacetSetSurface(
        args.payload.resolve(), "/facets/one_period", identity,
        periodic_caps="x0 y0", surface_id=903)
    box = coils.bounding_box('-')
    lower, upper = box.lower_left, box.upper_right
    if (lower[0] < -1e-9 or lower[1] < -1e-9
            or math.hypot(max(abs(lower[0]), abs(upper[0])),
                          max(abs(lower[1]), abs(upper[1]))) >= 2500
            or max(abs(lower[2]), abs(upper[2])) >= 700):
        raise ValueError("facet bounds exceed the positive x/y sector enclosure")
    radial = openmc.ZCylinder(r=2500.0, boundary_type="vacuum",
                              surface_id=904)
    zmin = openmc.ZPlane(-700.0, boundary_type="vacuum", surface_id=905)
    zmax = openmc.ZPlane(700.0, boundary_type="vacuum", surface_id=906)
    sector = +x0 & +y0 & -radial & +zmin & -zmax
    label = "accepted-mesh" if accepted else "derived-periodic-mesh"
    coil_cell = openmc.Cell(cell_id=1001, name=f"{label}-coil-region",
                            region=sector & -coils)
    complement = openmc.Cell(cell_id=1002, name=f"{label}-complement",
                             region=sector & +coils)
    args.output.mkdir(parents=True)
    xml = args.output / "geometry.xml"
    openmc.Geometry([coil_cell, complement]).export_to_xml(path=xml)
    openmc.reset_auto_ids()
    reloaded = openmc.Geometry.from_xml(path=xml, materials=openmc.Materials())
    cells = reloaded.get_all_cells()
    surfaces = reloaded.get_all_surfaces()
    if (set(cells) != {1001, 1002} or set(surfaces) != set(range(901, 907))
            or surfaces[901].periodic_surface is not surfaces[902]
            or surfaces[902].periodic_surface is not surfaces[901]
            or not surfaces[903].is_equal(coils)
            or str(cells[1001].region) != str(coil_cell.region)
            or str(cells[1002].region) != str(complement.region)
            or cells[1001].fill is not None or cells[1002].fill is not None):
        raise ValueError("facet period geometry roundtrip changed ownership")
    receipt = {
        "schema": "stellarcsg.facet-period-region/v1",
        "state": ("ACCEPTED_MESH_SECTOR_XML_ROUNDTRIP_ONLY" if accepted
                  else "DERIVED_PERIODIC_FACET_SECTOR_XML_ROUNDTRIP_ONLY"),
        "facet_source_classification": source["classification"],
        "field_period_degrees": 90,
        "facet_triangle_count": 3348,
        "facet_component_ids": list(range(8, 26)),
        "facet_content_id": identity,
        "periodic_caps": "x0 y0",
        "facet_box_lower_cm": list(map(float, lower)),
        "facet_box_upper_cm": list(map(float, upper)),
        "sector_halfspaces": ["x>=0", "y>=0"],
        "periodic_plane_ids": [901, 902],
        "facet_surface_id": 903,
        "coil_cell_id": 1001,
        "complement_cell_id": 1002,
        "hashes": {"builder": sha256(Path(__file__)),
                   "payload": sha256(args.payload),
                   "payload_receipt": sha256(args.payload_receipt),
                   "geometry_xml": sha256(xml)},
        "claim_boundary": ("Python XML contains two complementary unfilled cells in a 90-degree x/y sector, with a hash-bound P00 facet union, paired periodic planes and explicit facet cap delegation. The source classification identifies whether the payload preserves accepted H5M triangles or is a derived periodic candidate. Native seam ownership, mesh-to-continuous-CAD fidelity, histories, materials, source clearance and transport remain unqualified.")
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])


if __name__ == "__main__":
    main()
