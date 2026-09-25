"""Track one void-only source ray into each distinct derived P00 coil cell."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import openmc

from audit_periodic_facet_ray_bank import on_vacuum_boundary, point, sha256
from stage_facet_component_period_region import (
    CONTENT_ID, OVERLAP_AUDIT_SHA256, PAYLOAD_SHA256)


ACCEPTED_H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"
SIDE_BANK_SHA256 = "37918fd9c88c3b28a60366ab67a4e3599fbefacb446e1afaee4d515105a679e4"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--side-bank", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--cross-sections", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != repo / "openmc/__init__.py":
        raise ValueError("wrong Python OpenMC checkout")
    region_path = args.region / "geometry.xml"
    region = json.loads((args.region / "receipt.json").read_text())
    bank = json.loads(args.side_bank.read_text())
    geometry = ET.parse(region_path).getroot()
    surfaces = {int(node.get("id")): node for node in geometry.findall(".//surface")}
    cells = {int(node.get("id")): node for node in geometry.findall(".//cell")}
    if (region["state"] != "DERIVED_18_PRIORITY_VOID_CELLS_XML_ROUNDTRIP_ONLY"
            or region["hashes"]["geometry_xml"] != sha256(region_path)
            or region["hashes"]["payload"] != PAYLOAD_SHA256
            or region["hashes"]["overlap_audit"] != OVERLAP_AUDIT_SHA256
            or region["hashes"]["stager"] != sha256(
                Path(__file__).with_name("stage_facet_component_period_region.py"))
            or region["overlap_priority"] != "ascending_dagmc_volume_id_void_only"
            or region["known_overlap_pairs"] != [[15, 16], [17, 18]]
            or bank["classification"] != "P00_ACCEPTED_MESH_FACET_SIDE_CONTROLS"
            or sha256(args.side_bank) != SIDE_BANK_SHA256
            or bank["input_sha256"]["dagmc_h5m"] != ACCEPTED_H5M_SHA256
            or len(bank["rows"]) != 18
            or {row["dagmc_volume_id"] for row in bank["rows"]}
            != set(range(8, 26))
            or set(surfaces) != {901, 902, 904, 905, 906,
                                *range(1108, 1126)}
            or set(cells) != {2000, *range(2008, 2026)}):
        raise ValueError("component region or accepted side bank differs")
    for component in range(8, 26):
        facet = surfaces[1100 + component]
        cap = "y0" if component <= 13 else "" if component <= 19 else "x0"
        if (facet.get("type") != "facet-set"
                or facet.get("content_id") != CONTENT_ID
                or int(facet.get("component_id")) != component
                or facet.get("periodic_caps", "") != cap
                or sha256(Path(facet.get("data_file"))) != PAYLOAD_SHA256
                or cells[2000 + component].get("region") is None
                or f"-{1100 + component}" not in cells[2000 + component].get("region").split()
                or cells[2000 + component].get("material") != "void"):
            raise ValueError(f"component {component} surface/cell differs")
    for sid, other in ((901, 902), (902, 901)):
        if (surfaces[sid].get("boundary") != "periodic"
                or surfaces[sid].get("periodic_surface_id") != str(other)):
            raise ValueError("periodic plane pair differs")
    binary = args.binary.resolve()
    library = args.library.resolve()
    cross_sections = args.cross_sections.resolve()
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", LD_LIBRARY_PATH=str(library.parent),
               OPENMC_CROSS_SECTIONS=str(cross_sections))
    loader = subprocess.run(["ldd", str(binary)], env=env,
                            capture_output=True, text=True, timeout=10)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if loader.returncode or len(bindings) != 1 or str(library) not in bindings[0]:
        raise ValueError("OpenMC binary is not bound to selected library")
    args.output.mkdir(parents=True)
    results = []
    for row in bank["rows"]:
        volume_id = int(row["dagmc_volume_id"])
        case = args.output / f"volume-{volume_id:02d}"
        case.mkdir()
        shutil.copyfile(region_path, case / "geometry.xml")
        openmc.Materials().export_to_xml(path=case / "materials.xml")
        outside, inside = point(row, "outside"), point(row, "inside")
        direction = inside - outside
        direction /= np.linalg.norm(direction)
        settings = openmc.Settings()
        settings.run_mode = "fixed source"
        settings.particles = 1
        settings.batches = 1
        settings.inactive = 0
        settings.source = openmc.IndependentSource(
            space=openmc.stats.Point(outside),
            angle=openmc.stats.Monodirectional(direction),
            energy=openmc.stats.Discrete([1e6], [1.0]),
            particle="neutron")
        settings.track = [(1, 1, 1)]
        settings.output = {"summary": True, "tallies": False}
        settings.export_to_xml(path=case / "settings.xml")
        run = subprocess.run([str(binary)], cwd=case, env=env,
                             capture_output=True, text=True, timeout=30)
        result = {"dagmc_volume_id": volume_id, "expected_coil_cell_id": 2000 + volume_id,
                  "facet_id": row["facet_id"], "exit_code": run.returncode,
                  "stderr": run.stderr[-2000:],
                  "hashes": {name: sha256(case / name) for name in
                             ("geometry.xml", "settings.xml", "materials.xml")}}
        if (run.returncode == 0 and (case / "tracks.h5").exists()
                and (case / "statepoint.1.h5").exists()
                and (case / "summary.h5").exists()):
            with h5py.File(case / "statepoint.1.h5") as statepoint:
                run_identity = (statepoint.attrs.get("filetype") == b"statepoint"
                                and int(statepoint["n_particles"][()]) == 1
                                and int(statepoint["n_batches"][()]) == 1
                                and statepoint["run_mode"][()] == b"fixed source")
                statepoint_time = statepoint.attrs.get("date_and_time")
            with h5py.File(case / "tracks.h5") as tracks:
                track_identity = (tracks.attrs.get("filetype") == b"track"
                                  and set(tracks) == {"track_1_1_1"})
                states = tracks["track_1_1_1"][:] if track_identity else None
            openmc.reset_auto_ids()
            with h5py.File(case / "summary.h5") as summary:
                groups = summary["geometry/surfaces"]
                summary_time = summary.attrs.get("date_and_time")
                timestamps_consistent = False
                if statepoint_time is not None and summary_time is not None:
                    parse_time = lambda value: datetime.strptime(
                        value.decode(), "%Y-%m-%d %H:%M:%S")
                    elapsed = (parse_time(statepoint_time)
                               - parse_time(summary_time)).total_seconds()
                    timestamps_consistent = 0 <= elapsed <= 30
                summary_selectors = (summary.attrs.get("filetype") == b"summary"
                    and timestamps_consistent
                    and all(
                    openmc.Surface.from_hdf5(
                        groups[f"surface {1100 + cid}"]).component_id == cid
                    for cid in range(8, 26)))
            if run_identity and track_identity and summary_selectors and len(states) >= 3:
                cells_seen = states["cell_id"].tolist()
                first = np.array(tuple(states["r"][0]), dtype=float)
                first_direction = np.array(tuple(states["u"][0]), dtype=float)
                crossing = np.array(tuple(states["r"][1]), dtype=float)
                terminal = np.array(tuple(states["r"][-1]), dtype=float)
                error = float(np.linalg.norm(crossing - row["facet_centroid_cm"]))
                result.update({
                    "cell_sequence": cells_seen,
                    "first_crossing_cm": crossing.tolist(),
                    "first_crossing_centroid_error_cm": error,
                    "terminal_position_cm": terminal.tolist(),
                    "entry_and_leakage_pass": bool(
                        cells_seen[:2] == [2000, 2000 + volume_id]
                        and cells_seen[-1] == 2000
                        and np.allclose(first, outside, rtol=0, atol=1e-10)
                        and np.allclose(first_direction, direction, rtol=0, atol=1e-12)
                        and float(states["E"][0]) == 1e6
                        and error < 0.01
                        and np.all(states["material_id"] == -1)
                        and float(states["wgt"][-1]) == 0.0
                        and np.all(np.diff(states["time"]) > 0)
                        and on_vacuum_boundary(terminal, geometry)),
                    "hashes": {**result["hashes"], **{
                        name: sha256(case / name) for name in
                        ("tracks.h5", "statepoint.1.h5", "summary.h5")}}})
        results.append(result)
    passed = len(results) == 18 and all(row.get("entry_and_leakage_pass") for row in results)
    receipt = {
        "schema": "stellarcsg.component-facet-ray-bank/v1",
        "state": "PASS_18_DISTINCT_VOID_COIL_CELLS" if passed else "INCOMPLETE_COMPONENT_VOID_TRACKS",
        "rows": results,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "region_receipt": sha256(args.region / "receipt.json"),
                   "side_bank": sha256(args.side_bank),
                   "binary": sha256(binary), "library": sha256(library),
                   "cross_sections_index": sha256(cross_sections)},
        "claim_boundary": "One void-only ray per accepted P00 mesh group enters the matching deterministic-priority derived facet cell and terminates on the enclosure vacuum boundary. Facet shells 15-16 and 17-18 overlap, and ascending volume ID assigns their shared regions only for this void-only control. This does not establish physical material ownership, continuous CAD fidelity, material transport, full phase-space/edge coverage, plasma clearance, or performance."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"],
                      "passed": sum(bool(row.get("entry_and_leakage_pass")) for row in results)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
