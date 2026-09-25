"""Stage distinct unfilled P00 coil cells from one verified facet payload."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import openmc


PAYLOAD_SHA256 = "3db1723d250319d7e6e3d0a4cbbba7b88a68c830fba4214d001a8c2c2545c2d4"
CONTENT_ID = "sha256:2167ba06b820b747143de1a22f4704e67a538cdec217bf7ffa0fd9b418536f4c"
OVERLAP_AUDIT_SHA256 = "d61795613be034bd2fbef404dfe5c77492bef66aa519e219b5f20224d19dffc5"
CAP_COUNTS = {
    8: (0, 6), 9: (0, 16), 10: (0, 18), 11: (0, 18),
    12: (0, 16), 13: (0, 6),
    14: (0, 0), 15: (0, 0), 16: (0, 0), 17: (0, 0),
    18: (0, 0), 19: (0, 0),
    20: (6, 0), 21: (16, 0), 22: (18, 0), 23: (18, 0),
    24: (16, 0), 25: (6, 0),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--payload-receipt", type=Path, required=True)
    parser.add_argument("--overlap-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != (repo / "openmc/__init__.py"):
        raise ValueError("wrong OpenMC Python checkout")
    source = json.loads(args.payload_receipt.read_text())
    if (sha256(args.payload) != PAYLOAD_SHA256
            or source["output_h5_sha256"] != PAYLOAD_SHA256
            or source["content_id"] != CONTENT_ID
            or source["classification"]
            != "DERIVED_PERIODIC_CAP_CANDIDATE_NOT_ACCEPTED_H5M"):
        raise ValueError("derived P00 facet payload identity differs")
    overlap = json.loads(args.overlap_audit.read_text())
    if (sha256(args.overlap_audit) != OVERLAP_AUDIT_SHA256
            or overlap["state"] != "CONFIRMED_TRANSVERSE_OVERLAP_ACCEPTED_AND_DERIVED"
            or overlap["hashes"]["derived_payload"] != PAYLOAD_SHA256
            or not overlap["intersecting_triangle_pairs_bitwise_unchanged"]
            or {tuple(row["component_ids"])
                for row in overlap["derived"]["witnesses"]}
            != {(15, 16), (17, 18)}):
        raise ValueError("component overlap audit identity differs")
    with h5py.File(args.payload, "r") as handle:
        group = handle["facets/one_period"]
        vertices = np.asarray(group["triangle_vertices"], dtype="<f8")
        components = np.asarray(group["component_ids"], dtype="<i4")
        if group.attrs["content_id"] != CONTENT_ID:
            raise ValueError("HDF5 content ID differs")
    if vertices.shape != (3348, 3, 3) or components.shape != (3348,):
        raise ValueError("P00 facet array shape differs")
    observed = {}
    for component in sorted(CAP_COUNTS):
        own = components == component
        observed[component] = tuple(int(np.count_nonzero(
            own & (np.max(np.abs(vertices[:, :, axis]), axis=1) <= 2.5e-13)))
            for axis in (0, 1))
    if observed != CAP_COUNTS:
        raise ValueError("P00 component periodic cap counts differ")
    openmc.reset_auto_ids()
    x0 = openmc.XPlane(0.0, boundary_type="periodic", surface_id=901)
    y0 = openmc.YPlane(0.0, boundary_type="periodic", surface_id=902)
    x0.periodic_surface = y0
    radial = openmc.ZCylinder(r=2500.0, boundary_type="vacuum",
                              surface_id=904)
    zmin = openmc.ZPlane(-700.0, boundary_type="vacuum", surface_id=905)
    zmax = openmc.ZPlane(700.0, boundary_type="vacuum", surface_id=906)
    sector = +x0 & +y0 & -radial & +zmin & -zmax
    available_region = sector
    cells = []
    surfaces = {}
    for component, (x_caps, y_caps) in CAP_COUNTS.items():
        cap_selector = "x0" if x_caps else "y0" if y_caps else ""
        facet = openmc.FacetSetSurface(
            args.payload.resolve(), "/facets/one_period", CONTENT_ID,
            component_id=component, periodic_caps=cap_selector,
            surface_id=1100 + component)
        box = facet.bounding_box('-')
        selected_vertices = vertices[components == component].reshape(-1, 3)
        if (box.lower_left[0] < -1e-9 or box.lower_left[1] < -1e-9
                or np.max(np.hypot(selected_vertices[:, 0],
                                   selected_vertices[:, 1])) >= 2500 - 1e-9
                or min(box.lower_left[2], -box.upper_right[2]) <= -700):
            raise ValueError(f"selected component {component} leaves sector")
        surfaces[component] = facet
        cells.append(openmc.Cell(cell_id=2000 + component,
                                 name=f"P00-derived-volume-{component}",
                                 region=available_region & -facet))
        available_region = available_region & +facet
    cells.append(openmc.Cell(cell_id=2000, name="P00-derived-complement",
                             region=available_region))
    args.output.mkdir(parents=True)
    xml = args.output / "geometry.xml"
    openmc.Geometry(cells).export_to_xml(path=xml)
    openmc.reset_auto_ids()
    imported = openmc.Geometry.from_xml(path=xml, materials=openmc.Materials())
    read_cells = imported.get_all_cells()
    read_surfaces = imported.get_all_surfaces()
    if (set(read_cells) != {2000, *range(2008, 2026)}
            or set(read_surfaces) != {901, 902, 904, 905, 906,
                                     *range(1108, 1126)}
            or read_surfaces[901].periodic_surface is not read_surfaces[902]
            or read_surfaces[902].periodic_surface is not read_surfaces[901]
            or any(read_surfaces[1100 + component].component_id != component
                   or read_surfaces[1100 + component].periodic_caps
                   != surfaces[component].periodic_caps
                   for component in CAP_COUNTS)
            or any(cell.fill is not None for cell in read_cells.values())):
        raise ValueError("per-component sector XML roundtrip differs")
    receipt = {
        "schema": "stellarcsg.facet-component-period-region/v1",
        "state": "DERIVED_18_PRIORITY_VOID_CELLS_XML_ROUNDTRIP_ONLY",
        "field_period_degrees": 90,
        "coil_cell_ids": list(range(2008, 2026)),
        "dagmc_reference_volume_ids": list(range(8, 26)),
        "complement_cell_id": 2000,
        "facet_surface_ids": list(range(1108, 1126)),
        "component_cap_counts": {str(k): list(v) for k, v in CAP_COUNTS.items()},
        "overlap_priority": "ascending_dagmc_volume_id_void_only",
        "known_overlap_pairs": [[15, 16], [17, 18]],
        "hashes": {"stager": sha256(Path(__file__)),
                   "payload": sha256(args.payload),
                   "payload_receipt": sha256(args.payload_receipt),
                   "overlap_audit": sha256(args.overlap_audit),
                   "geometry_xml": sha256(xml)},
        "claim_boundary": "Python stages 18 distinct unfilled cells and one complement within a 90-degree sector. The accepted and derived facet shells intersect for volume pairs 15-16 and 17-18. Ascending volume ID masks later overlapping shells solely to give deterministic void-only test regions; no physical material priority is approved. Numeric labels follow DAGMC reference volume IDs, not raw filament indices. Native initialization, particle histories, material ownership and continuous CAD remain unqualified here."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])


if __name__ == "__main__":
    main()
