"""Run and audit one bounded, void-only periodic facet tracking smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--cross-sections", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    model = args.model.resolve()
    binary = args.binary.resolve()
    library = args.library.resolve()
    cross_sections = args.cross_sections.resolve()
    if (args.receipt.exists() or any((model / name).exists() for name in
            ("tracks.h5", "statepoint.1.h5", "summary.h5"))):
        parser.error("receipt and simulation outputs must be new")
    staged = json.loads((model / "receipt.json").read_text())
    if staged["state"] != "STAGED_VOID_ONLY_SOURCE_RAY":
        raise ValueError("not the staged tracking model")
    for name in ("geometry.xml", "settings.xml", "materials.xml"):
        if staged["hashes"][name.replace(".", "_")] != sha256(model / name):
            raise ValueError(f"staged {name} differs")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(library.parent)
    env["OPENMC_CROSS_SECTIONS"] = str(cross_sections)
    env["OMP_NUM_THREADS"] = "1"
    loader = subprocess.run(["ldd", str(binary)], env=env, check=False,
                            capture_output=True, text=True, timeout=10)
    bindings = [line for line in loader.stdout.splitlines()
                if "libopenmc.so" in line]
    if (loader.returncode or len(bindings) != 1
            or str(library) not in bindings[0]):
        raise ValueError("OpenMC executable has the wrong library binding")
    run = subprocess.run([str(binary)], cwd=model, env=env, check=False,
                         capture_output=True, text=True, timeout=60)
    if run.returncode or "FIXED SOURCE TRANSPORT SIMULATION" not in run.stdout:
        raise ValueError(f"OpenMC run failed: {run.returncode}: {run.stderr}")
    with h5py.File(model / "statepoint.1.h5", "r") as statepoint:
        if (int(statepoint["n_particles"][()]) != 10
                or int(statepoint["n_batches"][()]) != 1
                or statepoint["run_mode"][()] != b"fixed source"):
            raise ValueError("statepoint run identity differs")
    with h5py.File(model / "tracks.h5", "r") as tracks:
        if set(tracks) != {"track_1_1_1"}:
            raise ValueError("expected exactly one selected particle track")
        states = tracks["track_1_1_1"][:]
    cells = states["cell_id"].tolist()
    if (len(states) < 4 or cells[:4] != [1002, 1001, 1001, 1002]
            or int(states["material_id"][0]) != -1
            or not np.all(states["material_id"] == -1)
            or float(states["wgt"][-1]) != 0.0
            or cells[-1] != 1002):
        raise ValueError("void-only facet entry, periodic handoff or leakage differs")
    geometry = ET.parse(model / "geometry.xml")
    vacuum = {int(surface.get("id")): surface for surface in
              geometry.findall(".//surface")
              if surface.get("boundary") == "vacuum"}
    if set(vacuum) != {904, 905, 906}:
        raise ValueError("expected vacuum enclosure surfaces differ")
    cylinder = vacuum[904]
    lower_plane = vacuum[905]
    upper_plane = vacuum[906]
    if (cylinder.get("type") != "z-cylinder"
            or lower_plane.get("type") != "z-plane"
            or upper_plane.get("type") != "z-plane"):
        raise ValueError("vacuum enclosure types differ")
    cx, cy, radius = map(float, cylinder.get("coeffs").split())
    zmin = float(lower_plane.get("coeffs"))
    zmax = float(upper_plane.get("coeffs"))
    terminal = np.array(tuple(states["r"][-1]), dtype=float)
    terminal_radius = float(np.hypot(terminal[0] - cx, terminal[1] - cy))
    vacuum_surface = ("outer-cylinder" if abs(terminal_radius - radius) <= 1e-8
                      else "lower-z-plane" if abs(terminal[2] - zmin) <= 1e-8
                      else "upper-z-plane" if abs(terminal[2] - zmax) <= 1e-8
                      else None)
    if (not np.isfinite(terminal).all()
            or not np.isfinite((cx, cy, radius, zmin, zmax)).all()
            or not (zmin < zmax)
            or radius <= 0 or vacuum_surface is None
            or terminal[0] < -1e-8 or terminal[1] < -1e-8
            or terminal_radius > radius + 1e-8
            or terminal[2] < zmin - 1e-8 or terminal[2] > zmax + 1e-8):
        raise ValueError("terminal track state is not on a vacuum boundary")
    source = np.asarray(staged["source_outside_cm"], dtype=float)
    direction = np.asarray(staged["source_direction"], dtype=float)
    first = np.array(tuple(states["r"][0]), dtype=float)
    first_direction = np.array(tuple(states["u"][0]), dtype=float)
    periodic = np.array(tuple(states["r"][2]), dtype=float)
    periodic_direction = np.array(tuple(states["u"][2]), dtype=float)
    distance_to_y0 = -source[1] / direction[1]
    y0_hit = source + distance_to_y0 * direction
    rotated_hit = np.array((0.0, y0_hit[0], y0_hit[2]))
    rotated_direction = np.array((-direction[1], direction[0], direction[2]))
    if (not np.allclose(first, source, rtol=0, atol=1e-10)
            or not np.allclose(first_direction, direction, rtol=0, atol=1e-12)
            or not np.allclose(periodic, rotated_hit, rtol=0, atol=1e-8)
            or not np.allclose(periodic_direction, rotated_direction,
                               rtol=0, atol=1e-12)
            or not np.all(np.diff(states["time"]) > 0)):
        raise ValueError("tracked periodic position, direction or time differs")
    receipt = {
        "schema": "stellarcsg.periodic-facet-tracking-audit/v1",
        "state": "PASS_LOCAL_VOID_ONLY_PERIODIC_FACET_TRACK",
        "histories": 10, "selected_tracks": 1,
        "selected_track_cell_ids": cells,
        "selected_track_state_count": len(states),
        "periodic_handoff_cell_id": int(states["cell_id"][2]),
        "periodic_handoff_position_cm": periodic.tolist(),
        "periodic_handoff_direction": periodic_direction.tolist(),
        "terminal_position_cm": terminal.tolist(),
        "terminal_vacuum_surface": vacuum_surface,
        "exit_code": run.returncode,
        "stdout": run.stdout, "stderr": run.stderr,
        "loader_binding": bindings[0].strip(),
        "hashes": {
            "auditor": sha256(Path(__file__)),
            "staged_receipt": sha256(model / "receipt.json"),
            "geometry_xml": sha256(model / "geometry.xml"),
            "settings_xml": sha256(model / "settings.xml"),
            "materials_xml": sha256(model / "materials.xml"),
            "binary": sha256(binary), "library": sha256(library),
            "cross_sections_index": sha256(cross_sections),
            "tracks": sha256(model / "tracks.h5"),
            "statepoint": sha256(model / "statepoint.1.h5"),
            "summary": sha256(model / "summary.h5")},
        "claim_boundary": "Ten void-only OpenMC histories completed locally; one selected history entered a facet coil cell, crossed a rotational periodic plane while retaining that cell, then leaked at the vacuum enclosure. This is a geometry-tracking smoke only; it has no material interactions, physical source distribution, tally uncertainty, CAD fidelity, or matched performance claim."
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"state": receipt["state"], "cells": cells}))


if __name__ == "__main__":
    main()
