"""Track accepted P00 side probes in a one-material faceted magnet union."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import openmc

from audit_periodic_facet_ray_bank import sha256
from audit_p00_magnet_material_bank import (
    BINARY_SHA256, HISTORIES, LIBRARY_SHA256,
)
from audit_p00_magnet_material_smoke import (
    CROSS_SECTIONS_SHA256, REGION_RECEIPT_SHA256, REGION_XML_SHA256,
)
from stage_facet_component_period_region import (
    CONTENT_ID, OVERLAP_AUDIT_SHA256, PAYLOAD_SHA256,
)


MATERIAL_BANK_RECEIPT_SHA256 = "d70216c45c454feef68e20d76318ee77b79772764760ce3a4a8bb3644842a5da"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("region", "material-bank", "cross-sections", "binary",
                 "library", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new directory")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != repo / "openmc/__init__.py":
        raise ValueError("wrong Python OpenMC checkout")
    region_receipt = args.region / "receipt.json"
    region_xml = args.region / "geometry.xml"
    material_receipt = args.material_bank / "receipt.json"
    if (sha256(region_receipt) != REGION_RECEIPT_SHA256
            or sha256(region_xml) != REGION_XML_SHA256
            or sha256(material_receipt) != MATERIAL_BANK_RECEIPT_SHA256
            or sha256(args.cross_sections) != CROSS_SECTIONS_SHA256):
        raise ValueError("qualified input receipt or geometry differs")
    region = json.loads(region_receipt.read_text())
    bank = json.loads(material_receipt.read_text())
    if (region["state"] != "DERIVED_18_PRIORITY_VOID_CELLS_XML_ROUNDTRIP_ONLY"
            or region["hashes"]["payload"] != PAYLOAD_SHA256
            or region["hashes"]["overlap_audit"] != OVERLAP_AUDIT_SHA256
            or region["known_overlap_pairs"] != [[15, 16], [17, 18]]
            or bank["state"] != "PASS_SAMPLED_18_MAGNET_MATERIAL_ENTRIES"
            or bank["histories"] != HISTORIES
            or len(bank["source_rows"]) != 18
            or [row["dagmc_volume_id"] for row in bank["source_rows"]]
            != list(range(8, 26))):
        raise ValueError("accepted material-bank lineage differs")
    for name in ("source.h5", "materials.xml"):
        if sha256(args.material_bank / name) != bank["hashes"][name]:
            raise ValueError(f"material-bank {name} differs")
    tree = ET.parse(region_xml)
    root = tree.getroot()
    cells = root.findall(".//cell")
    surfaces = {int(node.get("id")): node for node in root.findall(".//surface")}
    if ({int(cell.get("id")) for cell in cells} != {2000, *range(2008, 2026)}
            or set(surfaces) != {901, 902, 904, 905, 906,
                                   *range(1108, 1126)}):
        raise ValueError("derived 18-cell sector differs")
    payload_paths = set()
    for volume_id in range(8, 26):
        surface = surfaces[1100 + volume_id]
        expected_caps = "y0" if volume_id <= 13 else (
            "" if volume_id <= 19 else "x0")
        if (surface.get("type") != "facet-set"
                or surface.get("dataset") != "/facets/one_period"
                or surface.get("content_id") != CONTENT_ID
                or surface.get("component_id") != str(volume_id)
                or surface.get("periodic_caps", "") != expected_caps
                or surface.get("data_file") is None):
            raise ValueError(f"facet selector {volume_id} differs")
        payload_paths.add(Path(surface.get("data_file")).resolve())
    if len(payload_paths) != 1 or sha256(next(iter(payload_paths))) != PAYLOAD_SHA256:
        raise ValueError("referenced facet payload differs")
    binary, library = args.binary.resolve(), args.library.resolve()
    if sha256(binary) != BINARY_SHA256 or sha256(library) != LIBRARY_SHA256:
        raise ValueError("selected native binary/library differs")
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", LD_LIBRARY_PATH=str(library.parent),
               OPENMC_CROSS_SECTIONS=str(args.cross_sections.resolve()))
    loader = subprocess.run(["ldd", str(binary)], capture_output=True,
                            text=True, timeout=10, env=env)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if loader.returncode or len(bindings) != 1 or str(library) not in bindings[0]:
        raise ValueError("binary is not bound to selected library")

    sector = "901 902 -904 905 -906"
    complement = root.find(".//cell[@id='2000']")
    if complement is None or complement.get("region") != sector + " " + " ".join(
            str(i) for i in range(1108, 1126)):
        raise ValueError("source complement differs")
    for cell in cells:
        root.remove(cell)
    ET.SubElement(root, "cell", {
        "id": "2000", "name": "P00-derived-magnet-union-complement",
        "material": "void", "region": complement.get("region"), "universe": "1"})
    ET.SubElement(root, "cell", {
        "id": "2001", "name": "P00-derived-common-magnet-union",
        "material": "7",
        "region": sector + " (" + " | ".join(
            "-" + str(i) for i in range(1108, 1126)) + ")",
        "universe": "1"})
    args.output.mkdir(parents=True)
    tree.write(args.output / "geometry.xml", encoding="utf-8", xml_declaration=True)
    for name in ("source.h5", "materials.xml"):
        shutil.copyfile(args.material_bank / name, args.output / name)
    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.particles = HISTORIES
    settings.batches = 1
    settings.inactive = 0
    settings.source = openmc.FileSource((args.output / "source.h5").resolve())
    settings.track = [(1, 1, i) for i in range(1, HISTORIES + 1)]
    settings.output = {"summary": True, "tallies": False}
    settings.export_to_xml(path=args.output / "settings.xml")

    run = subprocess.run([str(binary)], cwd=args.output, env=env,
                         capture_output=True, text=True, timeout=180)
    counts = {str(i): {"sampled": 0, "passed": 0, "failed": []}
              for i in range(8, 26)}
    unmatched = []
    statepoint_path = args.output / "statepoint.1.h5"
    summary_path = args.output / "summary.h5"
    track_path = args.output / "tracks.h5"
    run_identity = False
    if (run.returncode == 0 and statepoint_path.is_file()
            and summary_path.is_file() and track_path.is_file()):
        with h5py.File(statepoint_path) as statepoint:
            run_identity = (statepoint.attrs.get("filetype") == b"statepoint"
                            and int(statepoint["n_particles"][()]) == HISTORIES
                            and int(statepoint["n_batches"][()]) == 1
                            and statepoint["run_mode"][()] == b"fixed source")
        with h5py.File(track_path) as tracks:
            track_identity = tracks.attrs.get("filetype") == b"track"
            for history in range(1, HISTORIES + 1):
                key = f"track_1_1_{history}"
                if key not in tracks:
                    unmatched.append({"history": history, "reason": "missing_track"})
                    continue
                states = tracks[key][:]
                if len(states) < 2:
                    unmatched.append({"history": history, "reason": "short_track"})
                    continue
                initial = np.asarray(tuple(states["r"][0]), dtype=float)
                matches = [row for row in bank["source_rows"]
                           if np.allclose(initial, row["outside_cm"], rtol=0,
                                          atol=1e-10)]
                if len(matches) != 1:
                    unmatched.append({"history": history,
                                      "reason": "ambiguous_source_position"})
                    continue
                row = matches[0]
                volume_id = str(row["dagmc_volume_id"])
                result = counts[volume_id]
                result["sampled"] += 1
                passed = bool(
                    track_identity and run_identity
                    and states["cell_id"][:2].tolist() == [2000, 2001]
                    and states["material_id"][:2].tolist() == [-1, 7]
                    and np.allclose(tuple(states["u"][0]), row["direction"],
                                    rtol=0, atol=1e-12)
                    and float(states["E"][0]) == 1e6
                    and np.linalg.norm(np.asarray(tuple(states["r"][1]))
                                       - row["facet_centroid_cm"]) < 0.01)
                if passed:
                    result["passed"] += 1
                else:
                    result["failed"].append(history)
    passed = (run.returncode == 0 and run_identity and not unmatched
              and all(row["sampled"] > 0 and row["passed"] == row["sampled"]
                      for row in counts.values()))
    filenames = ("geometry.xml", "materials.xml", "settings.xml", "source.h5",
                 "tracks.h5", "statepoint.1.h5", "summary.h5")
    receipt = {
        "schema": "stellarcsg.p00-magnet-union-bank/v1",
        "state": "PASS_SAMPLED_18_MAGNET_UNION_ENTRIES" if passed
                 else "INCOMPLETE_SAMPLED_MAGNET_UNION_ENTRIES",
        "histories": HISTORIES, "per_source_volume": counts, "unmatched": unmatched,
        "run": {"exit_code": run.returncode, "run_identity": run_identity,
                "stdout_tail": run.stdout[-3000:], "stderr_tail": run.stderr[-2000:]},
        "hashes": {"auditor": sha256(Path(__file__)),
                   "priority_region_receipt": sha256(region_receipt),
                   "priority_material_bank_receipt": sha256(material_receipt),
                   "facet_payload": sha256(next(iter(payload_paths))),
                   "cross_sections_index": sha256(args.cross_sections),
                   "binary": sha256(binary), "library": sha256(library),
                   **{name: sha256(args.output / name)
                      for name in filenames if (args.output / name).is_file()}},
        "claim_boundary": "The common accepted magnet material is represented by one Boolean union cell rather than arbitrary overlap priority. A bounded 360-history local 1 MeV facet-side source sample first enters that material union for all 18 labeled source groups. The labels identify source probes, not per-coil transport ownership. This does not qualify continuous CAD, plasma-source/wall clearance, collision physics, statistical tallies, generic import, or matched performance.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
