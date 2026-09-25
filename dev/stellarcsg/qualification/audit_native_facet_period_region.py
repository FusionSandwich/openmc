"""Bind native facet-sector initialization and remote-plane controls to inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import h5py
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def invoke(binary: Path, arguments: list[str], library: Path) -> dict:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(library.resolve().parent)
    env["OMP_NUM_THREADS"] = "1"
    loader = subprocess.run(["ldd", str(binary.resolve())], env=env,
                            capture_output=True, text=True, timeout=10,
                            check=False)
    binding = [line.strip() for line in loader.stdout.splitlines()
               if "libopenmc.so" in line]
    if (loader.returncode or len(binding) != 1
            or str(library.resolve()) not in binding[0]):
        raise ValueError(f"{binary} is not bound to the selected library")
    result = subprocess.run([str(binary.resolve()), *arguments],
                            env=env, capture_output=True, text=True,
                            timeout=60, check=False)
    return {"exit_code": result.returncode, "stdout": result.stdout,
            "stderr": result.stderr, "loader_binding": binding[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region-binary", type=Path, required=True)
    parser.add_argument("--particle-binary", type=Path, required=True)
    parser.add_argument("--seam-binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--region", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--selector-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory must be new")
    prior = json.loads((args.region / "receipt.json").read_text())
    selector = json.loads(args.selector_receipt.read_text())
    classification = prior.get(
        "facet_source_classification", "ACCEPTED_P00_TRIANGLES_PRESERVED_IN_HDF5")
    selector_classification = selector.get(
        "payload_classification", "ACCEPTED_P00_TRIANGLES_PRESERVED_IN_HDF5")
    if (prior["state"] not in (
            "ACCEPTED_MESH_SECTOR_XML_ROUNDTRIP_ONLY",
            "DERIVED_PERIODIC_FACET_SECTOR_XML_ROUNDTRIP_ONLY")
            or prior["hashes"]["geometry_xml"] != sha256(args.region / "geometry.xml")
            or prior["hashes"]["payload"] != sha256(args.payload)
            or prior["periodic_caps"] != "x0 y0"
            or selector["state"] != "PASS_NATIVE_REGISTRATION_ONLY"
            or selector_classification != classification
            or selector["hashes"]["payload_receipt"]
            != prior["hashes"]["payload_receipt"]
            or selector["hashes"]["library"] != sha256(args.library)
            or selector["hashes"]["payload"] != sha256(args.payload)):
        raise ValueError("region, payload, library or selector receipt mismatch")
    args.output.mkdir(parents=True)
    unpaired_dir = args.output / "unpaired-cap-planes-negative"
    unpaired_dir.mkdir()
    unpaired_tree = ET.parse(args.region / "geometry.xml")
    for surface_id in ("901", "902"):
        plane = unpaired_tree.find(f".//surface[@id='{surface_id}']")
        if plane is None or plane.get("coeffs") != "0.0" \
                or plane.get("boundary") != "periodic":
            raise ValueError("expected paired zero plane missing from staged region")
        plane.set("boundary", "transmission")
        plane.attrib.pop("periodic_surface_id", None)
    unpaired_xml = unpaired_dir / "geometry.xml"
    unpaired_tree.write(unpaired_xml, encoding="utf-8", xml_declaration=True)
    with h5py.File(args.payload, "r") as handle:
        vertices = handle["facets/one_period/triangle_vertices"][:]
    planar_caps = {axis: int(np.count_nonzero(
        np.max(np.abs(vertices[:, :, axis]), axis=1) < 1e-10))
        for axis in (0, 1)}
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    native = invoke(args.region_binary, [str(args.region.resolve())], args.library)
    periodic = invoke(args.particle_binary,
                      [str(args.region.resolve())], args.library)
    seam = invoke(args.seam_binary,
                  [str(args.region.resolve()), str(args.payload.resolve()),
                   prior["facet_content_id"]], args.library)
    unpaired = invoke(args.region_binary, [str(unpaired_dir.resolve())],
                      args.library)
    unpaired_rejected = (unpaired["exit_code"] != 0
                         and "Periodic facet caps require reciprocal x=0/y=0 rotation"
                         in re.sub(r"\s+", " ", unpaired["stderr"]))
    expected_native = {"state": "NATIVE_FACET_PERIOD_REGION_INITIALIZED",
                       "surfaces": 6, "cells": 2,
                       "rotational_periodic_pair": [901, 902],
                       "facet_surface_id": 903, "transport_run": False}
    expected_periodic = {"state": "NATIVE_PERIOD_PARTICLE_CROSSINGS_PASS",
                         "crossings": 2, "cell_id": 1002,
                         "transport_histories": 0}
    expected_seam = {"cap_count": [80, 80], "facet_first": [0, 0],
                     "periodic_plane_first": [80, 80],
                     "coil_handoff": [80, 80],
                     "further_facet_hit": [0, 0], "histories": 0}
    passed = (native["exit_code"] == 0 and not native["stderr"]
              and native["stdout"].splitlines() == [json.dumps(
                  expected_native, separators=(",", ":"))]
              and periodic["exit_code"] == 0 and not periodic["stderr"]
              and periodic["stdout"].splitlines() == [json.dumps(
                  expected_periodic, separators=(",", ":"))]
              and seam["exit_code"] == 0 and not seam["stderr"]
              and seam["stdout"].splitlines() == [json.dumps(
                  expected_seam, separators=(",", ":"))]
              and unpaired_rejected)
    receipt = {
        "schema": "stellarcsg.native-facet-period-region/v1",
        "state": "NATIVE_FACET_PERIOD_CONTROLS_PASS" if passed else "FAIL",
        "payload_classification": classification,
        "native_region": native,
        "periodic_plane_controls": periodic,
        "coil_cap_handoffs": seam,
        "unpaired_cap_planes_negative": unpaired,
        "unpaired_caps_rejected": unpaired_rejected,
        "plane_cap_triangles": {"x_zero": planar_caps[0],
                                 "y_zero": planar_caps[1]},
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {
            "auditor": sha256(Path(__file__)),
            "region_helper": sha256(args.region_binary),
            "particle_helper": sha256(args.particle_binary),
            "seam_helper": sha256(args.seam_binary),
            "libopenmc": sha256(args.library),
            "geometry_xml": sha256(args.region / "geometry.xml"),
            "unpaired_geometry_xml": sha256(unpaired_xml),
            "python_region_receipt": sha256(args.region / "receipt.json"),
            "selector_receipt": sha256(args.selector_receipt),
            "payload": sha256(args.payload),
        },
        "claim_boundary": "The classified P00 facet union initializes natively in a 90-degree sector. Two complement particles cross the periodic planes at radius 2300 cm; 160 cap-interior coil particles select a periodic plane first and map back into the coil cell. An unpaired x=0/y=0 cap model is rejected before geometry use. This qualifies those deterministic cap points, not all seam edges, non-cap coil crossings, histories, materials, source clearance, continuous CAD fidelity or transport performance."
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"],
                      "plane_cap_triangles": receipt["plane_cap_triangles"]}))
    if not passed:
        raise RuntimeError("native facet period controls failed")


if __name__ == "__main__":
    main()
