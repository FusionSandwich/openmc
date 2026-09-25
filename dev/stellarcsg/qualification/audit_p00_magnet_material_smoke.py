"""Run one local P00 magnet-material ray in the derived facet sector."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as StdET

import h5py
from lxml import etree
import numpy as np
import openmc

from audit_periodic_facet_ray_bank import point, sha256
from stage_facet_component_period_region import (
    OVERLAP_AUDIT_SHA256, PAYLOAD_SHA256)


H5M_SHA256 = "549c42bf66b290f8f56b6f4d7523940c3b32b9d256d993ea42605f4dddb33e39"
MODEL_SHA256 = "afee680e3fe7e1e417bb37e289f2ce775fe16fb8fc11298237ea3d959c864027"
SMOKE_RECEIPT_SHA256 = "716ed09c45402c47e9f480f495358260b8c9d1112233a36519916e9a4ab35931"
CROSS_SECTIONS_SHA256 = "218236803b2c4a21b038992af93dacfdfe5c0c0401cbbc57f3ff3a947c63abc7"
SIDE_BANK_SHA256 = "37918fd9c88c3b28a60366ab67a4e3599fbefacb446e1afaee4d515105a679e4"
REGION_RECEIPT_SHA256 = "7796088ae3374a549fd5ad3e86e0e85e072a6d52729cae721fb8c0e3a0a2deed"
REGION_XML_SHA256 = "d8190f303fe37d256f94e54ebc70b69265468db6fcebc9a62ecd98c735f29b3b"


def h5m_magnet_volume_ids(path: Path) -> list[int]:
    with h5py.File(path) as handle:
        root = handle["tstt"]
        names = root["tags/NAME"]
        named = {bytes(value).rstrip(b"\0").decode(): int(key)
                 for key, value in zip(names["id_list"][:], names["values"][:], strict=True)}
        magnet_group = named["mat:magnets"]
        sets = root["sets"]
        rows = sets["list"][:]
        start = int(sets["list"].attrs["start_id"])
        index = magnet_group - start
        row = rows[index]
        if int(row[3]) != 10:
            raise ValueError("magnet material group is not range-compressed")
        begin = int(rows[index - 1, 0]) + 1 if index else 0
        data = sets["contents"][begin:int(row[0]) + 1]
        if len(data) % 2:
            raise ValueError("invalid magnet group content ranges")
        members = [value for first, count in data.reshape(-1, 2)
                   for value in range(int(first), int(first + count))]
        global_ids = sets["tags/GLOBAL_ID"][:]
        return [int(global_ids[value - start]) for value in members]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--side-bank", type=Path, required=True)
    parser.add_argument("--h5m", type=Path, required=True)
    parser.add_argument("--model-xml", type=Path, required=True)
    parser.add_argument("--smoke-receipt", type=Path, required=True)
    parser.add_argument("--cross-sections", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--volume-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new directory")
    if not 8 <= args.volume_id <= 25:
        parser.error("volume-id must be 8 through 25")
    repo = Path(__file__).resolve().parents[3]
    if Path(openmc.__file__).resolve() != repo / "openmc/__init__.py":
        raise ValueError("wrong Python OpenMC checkout")
    source_receipt = json.loads(args.smoke_receipt.read_text())
    region = json.loads((args.region / "receipt.json").read_text())
    bank = json.loads(args.side_bank.read_text())
    if (sha256(args.h5m) != H5M_SHA256
            or sha256(args.model_xml) != MODEL_SHA256
            or sha256(args.smoke_receipt) != SMOKE_RECEIPT_SHA256
            or source_receipt["dagmc"]["sha256"] != H5M_SHA256
            or source_receipt["model_xml"]["sha256"] != MODEL_SHA256
            or sha256(args.side_bank) != SIDE_BANK_SHA256
            or bank["input_sha256"]["dagmc_h5m"] != H5M_SHA256
            or sha256(args.region / "receipt.json") != REGION_RECEIPT_SHA256
            or sha256(args.region / "geometry.xml") != REGION_XML_SHA256
            or region["state"] != "DERIVED_18_PRIORITY_VOID_CELLS_XML_ROUNDTRIP_ONLY"
            or region["hashes"]["payload"] != PAYLOAD_SHA256
            or region["hashes"]["stager"] != sha256(
                Path(__file__).with_name("stage_facet_component_period_region.py"))
            or region["hashes"]["overlap_audit"] != OVERLAP_AUDIT_SHA256
            or region["hashes"]["geometry_xml"] != REGION_XML_SHA256
            or region["known_overlap_pairs"] != [[15, 16], [17, 18]]
            or h5m_magnet_volume_ids(args.h5m) != list(range(8, 26))):
        raise ValueError("accepted P00 magnet geometry/material lineage differs")
    material_node = etree.parse(str(args.model_xml)).find(".//material[@id='7']")
    if material_node is None:
        raise ValueError("accepted magnet material 7 is absent")
    material = openmc.Material.from_xml_element(material_node)
    nuclides = set(material.get_nuclides())
    if (material.id != 7 or material.name != "magnets"
            or material.density_units != "g/cm3"
            or material.density != 7.957317449024001
            or len(nuclides) != 51):
        raise ValueError("accepted magnet material definition differs")
    if sha256(args.cross_sections) != CROSS_SECTIONS_SHA256:
        raise ValueError("local full neutron cross-section index differs")
    library = openmc.data.DataLibrary.from_xml(args.cross_sections)
    relevant = [row for row in library.libraries
                if row["type"] == "neutron" and nuclides.intersection(row["materials"])]
    for nuclide in nuclides:
        matches = [row for row in relevant if nuclide in row["materials"]]
        if len(matches) != 1 or not Path(matches[0]["path"]).is_file():
            raise ValueError(f"missing or ambiguous local neutron data: {nuclide}")
    row = next(row for row in bank["rows"]
               if row["dagmc_volume_id"] == args.volume_id)
    outside, inside = point(row, "outside"), point(row, "inside")
    direction = inside - outside
    direction /= np.linalg.norm(direction)
    binary = args.binary.resolve()
    native_library = args.library.resolve()
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
    tree = StdET.parse(args.region / "geometry.xml")
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
    settings = openmc.Settings()
    settings.run_mode = "fixed source"
    settings.particles = 1
    settings.batches = 1
    settings.inactive = 0
    settings.source = openmc.IndependentSource(
        space=openmc.stats.Point(outside),
        angle=openmc.stats.Monodirectional(direction),
        energy=openmc.stats.Discrete([1e6], [1.0]), particle="neutron")
    settings.track = [(1, 1, 1)]
    settings.output = {"summary": True, "tallies": False}
    settings.export_to_xml(path=args.output / "settings.xml")
    run = subprocess.run([str(binary)], cwd=args.output, env=env,
                         capture_output=True, text=True, timeout=120)
    outcome = {"exit_code": run.returncode,
               "stdout_tail": run.stdout[-3000:], "stderr_tail": run.stderr[-2000:]}
    track_path = args.output / "tracks.h5"
    statepoint_path = args.output / "statepoint.1.h5"
    summary_path = args.output / "summary.h5"
    if (run.returncode == 0 and track_path.is_file()
            and statepoint_path.is_file() and summary_path.is_file()):
        with h5py.File(track_path) as tracks:
            if set(tracks) == {"track_1_1_1"}:
                states = tracks["track_1_1_1"][:]
            else:
                states = None
        with h5py.File(statepoint_path) as statepoint:
            run_identity = (int(statepoint["n_particles"][()]) == 1
                            and int(statepoint["n_batches"][()]) == 1
                            and statepoint["run_mode"][()] == b"fixed source")
        if run_identity and states is not None and len(states) >= 2:
            cells_seen = states["cell_id"].tolist()
            materials_seen = states["material_id"].tolist()
            outcome.update({"cell_sequence": cells_seen,
                            "material_sequence": materials_seen,
                            "first_entry_cm": list(map(float, states["r"][1])),
                            "entry_pass": bool(
                                cells_seen[:2] == [2000, 2000 + args.volume_id]
                                and materials_seen[:2] == [-1, 7]
                                and np.allclose(tuple(states["r"][0]), outside,
                                                rtol=0, atol=1e-10)
                                and np.allclose(tuple(states["u"][0]), direction,
                                                rtol=0, atol=1e-12)
                                and float(states["E"][0]) == 1e6)})
    passed = bool(outcome.get("entry_pass"))
    filenames = ("geometry.xml", "materials.xml", "settings.xml",
                 "tracks.h5", "statepoint.1.h5", "summary.h5")
    receipt = {
        "schema": "stellarcsg.p00-magnet-material-smoke/v1",
        "state": "PASS_LOCAL_MAGNET_MATERIAL_ENTRY" if passed else "INCOMPLETE_LOCAL_MAGNET_MATERIAL_ENTRY",
        "volume_id": args.volume_id,
        "expected_cell_id": 2000 + args.volume_id,
        "source_outside_cm": outside.tolist(),
        "source_direction": direction.tolist(),
        "material": {"id": 7, "name": "magnets", "nuclides": 51,
                     "density_g_cm3": material.density},
        "cross_section_neutron_files": len(relevant),
        "cross_section_neutron_bytes": sum(Path(row["path"]).stat().st_size
                                           for row in relevant),
        "outcome": outcome,
        "hashes": {"auditor": sha256(Path(__file__)),
                   "region_receipt": sha256(args.region / "receipt.json"),
                   "side_bank": sha256(args.side_bank),
                   "h5m": sha256(args.h5m),
                   "model_xml": sha256(args.model_xml),
                   "smoke_receipt": sha256(args.smoke_receipt),
                   "cross_sections_index": sha256(args.cross_sections),
                   "binary": sha256(binary), "library": sha256(native_library),
                   **{name: sha256(args.output / name)
                      for name in filenames if (args.output / name).is_file()}},
        "claim_boundary": "One fixed 1 MeV neutron ray from an accepted facet side probe enters a deterministic-priority P00 coil cell filled with the accepted H5M's common magnet material 7. This is local material-loading and first-entry tracking only; it does not qualify plasma source, whole one-period wall/plasma materials, collision physics benchmark, tallies, CAD fidelity, material priority for per-coil attribution, or performance."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["state"])
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
