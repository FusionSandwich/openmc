"""Stage a bounded void-only source ray through a P00 facet for OpenMC."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import openmc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--selector-receipt", type=Path, required=True)
    parser.add_argument("--side-bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    region_receipt = json.loads((args.region / "receipt.json").read_text())
    selector_receipt = json.loads(args.selector_receipt.read_text())
    if (region_receipt["state"]
            != "DERIVED_PERIODIC_FACET_SECTOR_XML_ROUNDTRIP_ONLY"
            or region_receipt["hashes"]["geometry_xml"]
            != sha256(args.region / "geometry.xml")
            or selector_receipt["state"] != "PASS_NATIVE_REGISTRATION_ONLY"
            or selector_receipt["hashes"]["payload"]
            != region_receipt["hashes"]["payload"]):
        raise ValueError("derived facet sector and selector differ")
    side_bank = json.loads(args.side_bank.read_text())
    if (side_bank["classification"] != "P00_ACCEPTED_MESH_FACET_SIDE_CONTROLS"
            or side_bank["probe_count"] != 108):
        raise ValueError("P00 side bank differs")
    row = side_bank["rows"][0]
    probes = {probe["side"]: probe for probe in row["probes"]
              if probe["offset_cm"] == 0.2}
    outside = np.asarray(probes["outside"]["point_cm"], dtype=float)
    inside = np.asarray(probes["inside"]["point_cm"], dtype=float)
    direction = inside - outside
    direction /= np.linalg.norm(direction)
    if (np.min(outside[:2]) <= 0.0 or np.min(inside[:2]) <= 0.0
            or not np.isfinite(direction).all()):
        raise ValueError("selected source ray is not finite and sector interior")
    args.output.mkdir(parents=True)
    geometry_path = args.output / "geometry.xml"
    shutil.copyfile(args.region / "geometry.xml", geometry_path)
    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.particles = 10
    settings.batches = 1
    settings.inactive = 0
    settings.source = openmc.IndependentSource(
        space=openmc.stats.Point(outside),
        angle=openmc.stats.Monodirectional(direction),
        energy=openmc.stats.Discrete([1e6], [1.0]),
        particle="neutron")
    settings.track = [(1, 1, 1)]
    settings.output = {"summary": True, "tallies": False}
    settings.export_to_xml(path=args.output / "settings.xml")
    openmc.Materials().export_to_xml(path=args.output / "materials.xml")
    receipt = {
        "schema": "stellarcsg.periodic-facet-tracking-smoke/v1",
        "state": "STAGED_VOID_ONLY_SOURCE_RAY",
        "histories_requested": 10,
        "source_dagmc_volume_id": row["dagmc_volume_id"],
        "source_outside_cm": list(map(float, outside)),
        "reference_inside_cm": list(map(float, inside)),
        "source_direction": list(map(float, direction)),
        "hashes": {
            "stager": sha256(Path(__file__)),
            "region_receipt": sha256(args.region / "receipt.json"),
            "selector_receipt": sha256(args.selector_receipt),
            "side_bank": sha256(args.side_bank),
            "geometry_xml": sha256(geometry_path),
            "settings_xml": sha256(args.output / "settings.xml"),
            "materials_xml": sha256(args.output / "materials.xml")},
        "claim_boundary": "A fixed, monodirectional neutron source starts at an accepted P00 exterior side probe and points through its paired interior probe in a void-only 90-degree derived-facet sector. This stages a bounded geometry-tracking smoke; no physical material interactions, source distribution, dosimetry or performance are claimed."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])


if __name__ == "__main__":
    main()
