"""Sample all accepted P00 coil-side probes with accepted common magnet material."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import h5py
from lxml import etree
import numpy as np
import openmc

from audit_periodic_facet_ray_bank import point, sha256
from audit_p00_magnet_material_smoke import (
    CROSS_SECTIONS_SHA256, H5M_SHA256, MODEL_SHA256, REGION_RECEIPT_SHA256,
    REGION_XML_SHA256, SIDE_BANK_SHA256, SMOKE_RECEIPT_SHA256,
    h5m_magnet_volume_ids,
)
from stage_facet_component_period_region import (
    CONTENT_ID, OVERLAP_AUDIT_SHA256, PAYLOAD_SHA256,
)


HISTORIES = 360
BINARY_SHA256 = "dd0f316e5bd0965092f2a080167da9bbde83416392b6473763063fd95ec63dde"
LIBRARY_SHA256 = "fbc38dedc17e20342a56dd50e2d56f86330238dae00b95ab3e4602864967cba4"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "side-bank", "h5m", "model-xml", "smoke-receipt",
                 "cross-sections", "binary", "library", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new directory")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != repo / "openmc/__init__.py":
        raise ValueError("wrong Python OpenMC checkout")
    region_file = args.region / "receipt.json"
    region_xml = args.region / "geometry.xml"
    if (sha256(args.h5m) != H5M_SHA256
            or sha256(args.model_xml) != MODEL_SHA256
            or sha256(args.smoke_receipt) != SMOKE_RECEIPT_SHA256
            or sha256(args.side_bank) != SIDE_BANK_SHA256
            or sha256(region_file) != REGION_RECEIPT_SHA256
            or sha256(region_xml) != REGION_XML_SHA256
            or sha256(args.cross_sections) != CROSS_SECTIONS_SHA256):
        raise ValueError("accepted input hash differs")
    source_receipt = json.loads(args.smoke_receipt.read_text())
    region = json.loads(region_file.read_text())
    bank = json.loads(args.side_bank.read_text())
    if (source_receipt["dagmc"]["sha256"] != H5M_SHA256
            or source_receipt["model_xml"]["sha256"] != MODEL_SHA256
            or bank["input_sha256"]["dagmc_h5m"] != H5M_SHA256
            or region["state"] != "DERIVED_18_PRIORITY_VOID_CELLS_XML_ROUNDTRIP_ONLY"
            or region["hashes"]["payload"] != PAYLOAD_SHA256
            or region["hashes"]["overlap_audit"] != OVERLAP_AUDIT_SHA256
            or region["hashes"]["geometry_xml"] != REGION_XML_SHA256
            or region["hashes"]["stager"] != sha256(
                Path(__file__).with_name("stage_facet_component_period_region.py"))
            or region["known_overlap_pairs"] != [[15, 16], [17, 18]]
            or h5m_magnet_volume_ids(args.h5m) != list(range(8, 26))
            or [row["dagmc_volume_id"] for row in bank["rows"]]
            != list(range(8, 26))):
        raise ValueError("accepted P00 lineage differs")

    material_node = etree.parse(str(args.model_xml)).find(".//material[@id='7']")
    if material_node is None:
        raise ValueError("accepted magnet material 7 is absent")
    material = openmc.Material.from_xml_element(material_node)
    nuclides = set(material.get_nuclides())
    if (material.id != 7 or material.name != "magnets"
            or material.density_units != "g/cm3"
            or material.density != 7.957317449024001 or len(nuclides) != 51):
        raise ValueError("accepted magnet material differs")
    library = openmc.data.DataLibrary.from_xml(args.cross_sections)
    for nuclide in nuclides:
        matches = [row for row in library.libraries
                   if row["type"] == "neutron" and nuclide in row["materials"]]
        if len(matches) != 1 or not Path(matches[0]["path"]).is_file():
            raise ValueError(f"missing or ambiguous neutron data: {nuclide}")

    binary = args.binary.resolve()
    native_library = args.library.resolve()
    if sha256(binary) != BINARY_SHA256 or sha256(native_library) != LIBRARY_SHA256:
        raise ValueError("selected OpenMC binary or library differs")
    input_geometry = ET.parse(region_xml)
    facet_surfaces = {int(surface.get("id")): surface for surface in
                      input_geometry.findall(".//surface[@type='facet-set']")}
    if set(facet_surfaces) != {1100 + volume_id for volume_id in range(8, 26)}:
        raise ValueError("derived facet selectors differ")
    payload_paths = set()
    for volume_id in range(8, 26):
        surface = facet_surfaces[1100 + volume_id]
        expected_caps = "y0" if volume_id <= 13 else (
            "" if volume_id <= 19 else "x0")
        if (surface.get("dataset") != "/facets/one_period"
                or surface.get("content_id") != CONTENT_ID
                or surface.get("units") != "cm"
                or surface.get("periodic_caps", "") != expected_caps
                or surface.get("component_id") != str(volume_id)
                or surface.get("data_file") is None):
            raise ValueError(f"derived facet selector {volume_id} differs")
        payload_paths.add(Path(surface.get("data_file")).resolve())
    if len(payload_paths) != 1 or sha256(next(iter(payload_paths))) != PAYLOAD_SHA256:
        raise ValueError("referenced facet HDF5 payload differs")
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", LD_LIBRARY_PATH=str(native_library.parent),
               OPENMC_CROSS_SECTIONS=str(args.cross_sections.resolve()))
    loader = subprocess.run(["ldd", str(binary)], capture_output=True,
                            text=True, timeout=10, env=env)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if loader.returncode or len(bindings) != 1 or str(native_library) not in bindings[0]:
        raise ValueError("binary is not bound to selected native library")

    args.output.mkdir(parents=True)
    tree = input_geometry
    cells = tree.findall(".//cell")
    if {int(cell.get("id")) for cell in cells} != {2000, *range(2008, 2026)}:
        raise ValueError("region cell IDs differ")
    for cell in cells:
        if cell.get("material") != "void":
            raise ValueError("source region is not void-only")
        if int(cell.get("id")) != 2000:
            cell.set("material", "7")
    tree.write(args.output / "geometry.xml", encoding="utf-8", xml_declaration=True)
    openmc.Materials([material]).export_to_xml(path=args.output / "materials.xml")

    source_rows = []
    source_particles = []
    for row in bank["rows"]:
        outside, inside = point(row, "outside"), point(row, "inside")
        direction = inside - outside
        direction /= np.linalg.norm(direction)
        source_particles.append(openmc.SourceParticle(
            r=tuple(outside), u=tuple(direction), E=1e6,
            particle=openmc.ParticleType.NEUTRON))
        source_rows.append({"dagmc_volume_id": row["dagmc_volume_id"],
                            "facet_id": row["facet_id"],
                            "outside_cm": outside.tolist(),
                            "direction": direction.tolist(),
                            "facet_centroid_cm": row["facet_centroid_cm"]})
    source_file = args.output / "source.h5"
    openmc.write_source_file(source_particles, source_file)
    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.particles = HISTORIES
    settings.batches = 1
    settings.inactive = 0
    settings.source = openmc.FileSource(source_file.resolve())
    settings.track = [(1, 1, i) for i in range(1, HISTORIES + 1)]
    settings.output = {"summary": True, "tallies": False}
    settings.export_to_xml(path=args.output / "settings.xml")

    run = subprocess.run([str(binary)], cwd=args.output, env=env,
                         capture_output=True, text=True, timeout=180)
    results = {row["dagmc_volume_id"]: {"sampled": 0, "passed": 0,
               "failed_history_ids": []} for row in source_rows}
    unmatched = []
    statepoint_path = args.output / "statepoint.1.h5"
    track_path = args.output / "tracks.h5"
    summary_path = args.output / "summary.h5"
    run_identity = False
    if (run.returncode == 0 and statepoint_path.is_file()
            and track_path.is_file() and summary_path.is_file()):
        with h5py.File(statepoint_path) as statepoint:
            run_identity = (statepoint.attrs.get("filetype") == b"statepoint"
                            and int(statepoint["n_particles"][()]) == HISTORIES
                            and int(statepoint["n_batches"][()]) == 1
                            and statepoint["run_mode"][()] == b"fixed source")
        with h5py.File(track_path) as tracks:
            track_identity = tracks.attrs.get("filetype") == b"track"
            for history in range(1, HISTORIES + 1):
                name = f"track_1_1_{history}"
                if name not in tracks:
                    unmatched.append({"history": history, "reason": "missing_track"})
                    continue
                states = tracks[name][:]
                if len(states) < 2:
                    unmatched.append({"history": history, "reason": "short_track"})
                    continue
                initial = np.asarray(tuple(states["r"][0]), dtype=float)
                matches = [row for row in source_rows
                           if np.allclose(initial, row["outside_cm"], rtol=0, atol=1e-10)]
                if len(matches) != 1:
                    unmatched.append({"history": history,
                                      "reason": "ambiguous_source_position"})
                    continue
                row = matches[0]
                volume_id = row["dagmc_volume_id"]
                result = results[volume_id]
                result["sampled"] += 1
                crossing = np.asarray(tuple(states["r"][1]), dtype=float)
                passed = bool(
                    track_identity and run_identity
                    and states["cell_id"][:2].tolist() == [2000, 2000 + volume_id]
                    and states["material_id"][:2].tolist() == [-1, 7]
                    and np.allclose(tuple(states["u"][0]), row["direction"],
                                    rtol=0, atol=1e-12)
                    and float(states["E"][0]) == 1e6
                    and np.linalg.norm(crossing - row["facet_centroid_cm"]) < 0.01)
                if passed:
                    result["passed"] += 1
                else:
                    result["failed_history_ids"].append(history)
    passed = (run.returncode == 0 and run_identity and not unmatched
              and all(result["sampled"] > 0
                      and result["passed"] == result["sampled"]
                      for result in results.values()))
    filenames = ("geometry.xml", "materials.xml", "settings.xml", "source.h5",
                 "tracks.h5", "statepoint.1.h5", "summary.h5")
    receipt = {
        "schema": "stellarcsg.p00-magnet-material-bank/v1",
        "state": "PASS_SAMPLED_18_MAGNET_MATERIAL_ENTRIES" if passed
                 else "INCOMPLETE_SAMPLED_MAGNET_MATERIAL_ENTRIES",
        "histories": HISTORIES,
        "source_rows": source_rows,
        "per_volume": results,
        "unmatched": unmatched,
        "run": {"exit_code": run.returncode, "run_identity": run_identity,
                "stdout_tail": run.stdout[-3000:], "stderr_tail": run.stderr[-2000:]},
        "hashes": {"auditor": sha256(Path(__file__)),
                   "accepted_h5m": sha256(args.h5m),
                   "accepted_model_xml": sha256(args.model_xml),
                   "accepted_smoke_receipt": sha256(args.smoke_receipt),
                   "side_bank": sha256(args.side_bank),
                   "region_receipt": sha256(region_file),
                   "facet_payload": sha256(next(iter(payload_paths))),
                   "cross_sections_index": sha256(args.cross_sections),
                   "binary": sha256(binary), "library": sha256(native_library),
                   **{name: sha256(args.output / name)
                      for name in filenames if (args.output / name).is_file()}},
        "claim_boundary": "A bounded local 1 MeV file-source sample enters each of 18 deterministic-priority faceted coil cells with accepted common magnet material 7. Sources are sampled with replacement, so counts differ. This is not a plasma source, collision-physics benchmark, statistical tally qualification, continuous CAD or winding-pack clearance proof, or matched performance comparison.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
