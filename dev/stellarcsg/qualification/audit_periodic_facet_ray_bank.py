"""Run one void-only OpenMC history through each accepted P00 coil group."""

from __future__ import annotations

import argparse
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


ACCEPTED_H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"
SIDE_BANK_SHA256 = "37918fd9c88c3b28a60366ab67a4e3599fbefacb446e1afaee4d515105a679e4"
REGION_RECEIPT_SHA256 = "b9936c2741547e0fad1e7431eeeed655f974cbe0cf263559080e8b503997642e"
CANDIDATE_SHA256 = "3db1723d250319d7e6e3d0a4cbbba7b88a68c830fba4214d001a8c2c2545c2d4"
CANDIDATE_CONTENT_ID = "sha256:2167ba06b820b747143de1a22f4704e67a538cdec217bf7ffa0fd9b418536f4c"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def point(row, side: str) -> np.ndarray:
    probe = next(probe for probe in row["probes"]
                 if probe["offset_cm"] == 0.2 and probe["side"] == side)
    return np.asarray(probe["point_cm"], dtype=float)


def on_vacuum_boundary(position: np.ndarray, geometry: ET.Element) -> bool:
    surfaces = {int(node.get("id")): node for node in
                geometry.findall(".//surface")}
    if (set((904, 905, 906)) - surfaces.keys()
            or any(surfaces[i].get("boundary") != "vacuum"
                   for i in (904, 905, 906))):
        return False
    cylinder = surfaces[904]
    lower = surfaces[905]
    upper = surfaces[906]
    if (cylinder.get("type") != "z-cylinder"
            or lower.get("type") != "z-plane"
            or upper.get("type") != "z-plane"):
        return False
    cx, cy, radius = map(float, cylinder.get("coeffs").split())
    zmin = float(lower.get("coeffs"))
    zmax = float(upper.get("coeffs"))
    rho = float(np.hypot(position[0] - cx, position[1] - cy))
    return bool(
        np.isfinite(position).all()
        and np.isfinite((cx, cy, radius, zmin, zmax)).all()
        and radius > 0 and zmin < zmax
        and position[0] >= -1e-8 and position[1] >= -1e-8
        and rho <= radius + 1e-8
        and zmin - 1e-8 <= position[2] <= zmax + 1e-8
        and (abs(rho - radius) <= 1e-8
             or abs(position[2] - zmin) <= 1e-8
             or abs(position[2] - zmax) <= 1e-8))


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
    if Path(openmc.__file__).resolve() != (repo / "openmc/__init__.py"):
        raise ValueError("wrong Python OpenMC checkout")
    region = json.loads((args.region / "receipt.json").read_text())
    bank = json.loads(args.side_bank.read_text())
    geometry_path = args.region / "geometry.xml"
    geometry = ET.parse(geometry_path).getroot()
    facet = geometry.find(".//surface[@id='903']")
    x_plane = geometry.find(".//surface[@id='901']")
    y_plane = geometry.find(".//surface[@id='902']")
    if (region["state"] != "DERIVED_PERIODIC_FACET_SECTOR_XML_ROUNDTRIP_ONLY"
            or sha256(args.region / "receipt.json") != REGION_RECEIPT_SHA256
            or sha256(args.side_bank) != SIDE_BANK_SHA256
            or region["hashes"]["geometry_xml"] != sha256(geometry_path)
            or region["hashes"]["payload"] != CANDIDATE_SHA256
            or region["facet_content_id"] != CANDIDATE_CONTENT_ID
            or facet is None or facet.get("type") != "facet-set"
            or facet.get("content_id") != region["facet_content_id"]
            or facet.get("periodic_caps") != "x0 y0"
            or sha256(Path(facet.get("data_file"))) != region["hashes"]["payload"]
            or x_plane is None or y_plane is None
            or x_plane.get("type") != "x-plane"
            or y_plane.get("type") != "y-plane"
            or x_plane.get("boundary") != "periodic"
            or y_plane.get("boundary") != "periodic"
            or x_plane.get("coeffs") != "0.0"
            or y_plane.get("coeffs") != "0.0"
            or x_plane.get("periodic_surface_id") != "902"
            or y_plane.get("periodic_surface_id") != "901"
            or bank["classification"] != "P00_ACCEPTED_MESH_FACET_SIDE_CONTROLS"
            or bank["input_sha256"]["dagmc_h5m"] != ACCEPTED_H5M_SHA256
            or len(bank["rows"]) != 18
            or {row["dagmc_volume_id"] for row in bank["rows"]}
            != set(range(8, 26))):
        raise ValueError("derived sector or accepted P00 side bank differs")
    binary = args.binary.resolve()
    library = args.library.resolve()
    cross_sections = args.cross_sections.resolve()
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["LD_LIBRARY_PATH"] = str(library.parent)
    env["OPENMC_CROSS_SECTIONS"] = str(cross_sections)
    loader = subprocess.run(["ldd", str(binary)], env=env,
                            capture_output=True, text=True, timeout=10)
    bindings = [line.strip() for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if (loader.returncode or len(bindings) != 1
            or str(library) not in bindings[0]):
        raise ValueError("OpenMC executable is not bound to selected library")
    args.output.mkdir(parents=True)
    results = []
    for row in bank["rows"]:
        volume_id = int(row["dagmc_volume_id"])
        case = args.output / f"volume-{volume_id:02d}"
        case.mkdir()
        shutil.copyfile(geometry_path, case / "geometry.xml")
        openmc.Materials().export_to_xml(path=case / "materials.xml")
        outside = point(row, "outside")
        inside = point(row, "inside")
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
        settings.output = {"summary": False, "tallies": False}
        settings.export_to_xml(path=case / "settings.xml")
        run = subprocess.run([str(binary)], cwd=case, env=env,
                             capture_output=True, text=True, timeout=15)
        result = {"dagmc_volume_id": volume_id, "facet_id": row["facet_id"],
                  "exit_code": run.returncode, "stderr": run.stderr,
                  "source_outside_cm": outside.tolist(),
                  "source_direction": direction.tolist(),
                  "hashes": {"geometry_xml": sha256(case / "geometry.xml"),
                             "settings_xml": sha256(case / "settings.xml"),
                             "materials_xml": sha256(case / "materials.xml")}}
        if run.returncode == 0 and (case / "tracks.h5").exists():
            with h5py.File(case / "statepoint.1.h5", "r") as statepoint:
                run_identity = (int(statepoint["n_particles"][()]) == 1
                                and int(statepoint["n_batches"][()]) == 1
                                and statepoint["run_mode"][()] == b"fixed source")
            with h5py.File(case / "tracks.h5", "r") as tracks:
                track_identity = set(tracks) == {"track_1_1_1"}
                states = tracks["track_1_1_1"][:] if track_identity else None
            if run_identity and track_identity and len(states) >= 3:
                cells = states["cell_id"].tolist()
                first = np.array(tuple(states["r"][0]), dtype=float)
                first_direction = np.array(tuple(states["u"][0]), dtype=float)
                crossing = np.array(tuple(states["r"][1]), dtype=float)
                terminal = np.array(tuple(states["r"][-1]), dtype=float)
                centroid_error = float(np.linalg.norm(
                    crossing - np.asarray(row["facet_centroid_cm"])))
                result.update({
                    "cell_sequence": cells,
                    "first_crossing_cm": crossing.tolist(),
                    "first_crossing_centroid_error_cm": centroid_error,
                    "terminal_position_cm": terminal.tolist(),
                    "entry_and_leakage_pass": bool(
                        cells[:2] == [1002, 1001] and cells[-1] == 1002
                        and np.allclose(first, outside, rtol=0, atol=1e-10)
                        and np.allclose(first_direction, direction,
                                        rtol=0, atol=1e-12)
                        and float(states["E"][0]) == 1e6
                        and centroid_error < 0.01
                        and np.all(states["material_id"] == -1)
                        and float(states["wgt"][-1]) == 0.0
                        and np.all(np.diff(states["time"]) > 0)
                        and on_vacuum_boundary(terminal, geometry)),
                    "hashes": {**result["hashes"],
                               "tracks": sha256(case / "tracks.h5"),
                               "statepoint": sha256(case / "statepoint.1.h5")}})
        results.append(result)
    passed = (len(results) == 18 and all(row.get("entry_and_leakage_pass")
                                         for row in results))
    receipt = {
        "schema": "stellarcsg.periodic-facet-ray-bank/v1",
        "state": ("PASS_18_COIL_GROUP_VOID_TRACKS" if passed
                  else "INCOMPLETE_COIL_GROUP_VOID_TRACKS"),
        "field_period_degrees": 90,
        "coil_group_count": 18,
        "rows": results,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "region_receipt": sha256(args.region / "receipt.json"),
                   "side_bank": sha256(args.side_bank),
                   "binary": sha256(binary), "library": sha256(library),
                   "cross_sections_index": sha256(cross_sections)},
        "claim_boundary": "One separate void-only OpenMC history per accepted P00 coil group enters the derived facet union near a hashed accepted side-bank facet and ends on a vacuum enclosure boundary. This is an 18-ray geometry-tracking control, not material transport, CAD fidelity, all facet/edge coverage, plasma-source clearance or throughput qualification."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"],
                      "passed": sum(bool(row.get("entry_and_leakage_pass"))
                                    for row in results)}))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
