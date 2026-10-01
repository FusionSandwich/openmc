"""Bounded, frozen 20k P00 before/after and flat-ring diagnostic."""

import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "dev/stellarcsg/reports/coil-profile-20260926"
PREP = REPORT / "fixed-section-plan-010"
OUT = ROOT / "dev/stellarcsg/reports/p00-native-validation-20260930-03/transport"
OLD = ROOT.parent / "stellarcsg-local-continuation-20260925/build/native-local-20260925"
NEW = Path("/home/sman/builds/stellarcsg-p00-bbox-20260930-03")
XS = Path("/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/cross_sections.xml")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs():
    plan = json.loads((PREP / "PLAN.json").read_text())
    for filename, expected in plan["binding_hashes"].items():
        if sha(filename) != expected:
            raise RuntimeError(f"Frozen input changed: {filename}")
    for case, files in plan["xml_hashes"].items():
        for name, expected in files.items():
            if sha(PREP / case / name) != expected:
                raise RuntimeError(f"Frozen {case}/{name} changed")
    if sha(XS) != "218236803b2c4a21b038992af93dacfdfe5c0c0401cbbc57f3ff3a947c63abc7":
        raise RuntimeError("Cross section index changed")
    fe = XS.parent / "FENDL-3.1d_Fe56.h5"
    if sha(fe) != "18abc04dc9fd602948bafcf487323a1148681c75ee74e27863e843211fd6f1f8":
        raise RuntimeError("Fe56 data changed")
    if not (NEW / "bin/openmc").is_file() or not (NEW / "lib/libopenmc.so").is_file():
        raise RuntimeError("New native runtime absent")
    return plan


def add_local_tallies(path):
    tree = ET.parse(path)
    root = tree.getroot()
    mesh = ET.SubElement(root, "mesh", id="301")
    ET.SubElement(mesh, "dimension").text = "4 4 4"
    ET.SubElement(mesh, "lower_left").text = "850 0 -380"
    ET.SubElement(mesh, "upper_right").text = "950 100 -280"
    mesh_filter = ET.SubElement(root, "filter", id="301", type="mesh")
    ET.SubElement(mesh_filter, "bins").text = "301"
    for tally_id, filters in ((301, "301"), (302, "1 301")):
        tally = ET.SubElement(root, "tally", id=str(tally_id))
        ET.SubElement(tally, "filters").text = filters
        ET.SubElement(tally, "scores").text = "flux"
        ET.SubElement(tally, "estimator").text = "tracklength"
    for tally_id, filters in ((303, None), (304, "1")):
        tally = ET.SubElement(root, "tally", id=str(tally_id))
        if filters is not None:
            ET.SubElement(tally, "filters").text = filters
        ET.SubElement(tally, "scores").text = "events"
        ET.SubElement(tally, "estimator").text = "collision"
    tree.write(path, encoding="utf-8", xml_declaration=True)


def child_limits():
    resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def run_case(name, geometry, runtime):
    case = OUT / name
    case.mkdir()
    for filename in ("geometry.xml", "materials.xml", "settings.xml", "tallies.xml"):
        shutil.copy2(PREP / geometry / filename, case / filename)
    add_local_tallies(case / "tallies.xml")
    env = os.environ.copy()
    env.pop("LD_PRELOAD", None)
    env.update(OPENMC_CROSS_SECTIONS=str(XS), LD_LIBRARY_PATH=str(runtime / "lib"),
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    binary = runtime / "bin/openmc"
    loader = subprocess.run(["ldd", str(binary)], env=env, text=True,
                            capture_output=True, timeout=15)
    if loader.returncode or "not found" in loader.stdout or str(runtime / "lib/libopenmc.so") not in loader.stdout:
        raise RuntimeError(f"Native loader binding failed for {name}: {loader.stdout} {loader.stderr}")
    (case / "loader.txt").write_text(loader.stdout)
    start = time.monotonic()
    with (case / "stdout.txt").open("w") as stdout, (case / "stderr.txt").open("w") as stderr:
        child = subprocess.Popen([str(binary)], cwd=case, env=env,
                                 stdout=stdout, stderr=stderr,
                                 preexec_fn=child_limits, start_new_session=True)
        try:
            code = child.wait(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            raise RuntimeError(f"Native timeout: {name}")
    wall = time.monotonic() - start
    if code != 0:
        raise RuntimeError(f"Native exit {code}: {name}")
    output = (case / "stdout.txt").read_text() + (case / "stderr.txt").read_text()
    if any(word in output.lower() for word in ("lost particle", "unresolved", "fatal error")):
        raise RuntimeError(f"Tracking diagnostic: {name}")
    tallies = {}
    with h5py.File(case / "statepoint.20.h5") as statepoint:
        counters = {key: int(statepoint[key][()]) for key in
                    ("n_particles", "n_batches", "current_batch", "n_realizations")}
        if counters != dict(n_particles=1000, n_batches=20,
                            current_batch=20, n_realizations=20):
            raise RuntimeError(f"Incomplete histories: {name}")
        timers = {key: float(item[()]) for key, item in statepoint["runtime"].items()}
        for tally_id in (1, 2, 3, 301, 302, 303, 304):
            data = np.asarray(statepoint[f"tallies/tally {tally_id}/results"][()])
            if not np.isfinite(data).all():
                raise RuntimeError(f"Nonfinite tally {tally_id}: {name}")
            tallies[str(tally_id)] = data
    if np.count_nonzero(tallies["301"]) == 0:
        raise RuntimeError(f"Local mesh tally empty: {name}")
    collision_events = float(tallies["303"][..., 0].sum())
    cell_collision_events = float(tallies["304"][..., 0].sum())
    # The cell partition can differ by the final floating summation bit.
    # The original diagnostic driver used exact equality here and stopped
    # after all three native workers completed; the collector preserved them.
    if abs(collision_events - cell_collision_events) > 1e-10:
        raise RuntimeError(f"Collision event cell partition differs: {name}")
    receipt = dict(name=name, runtime=str(runtime), binary_sha256=sha(binary),
                   library_sha256=sha(runtime / "lib/libopenmc.so"),
                   xml_sha256={p.name: sha(p) for p in case.glob("*.xml")},
                   statepoint_sha256=sha(case / "statepoint.20.h5"),
                   histories=20000, counters=counters, timers=timers,
                   transport_seconds=timers["transport"],
                   initialization_seconds=timers["total initialization"],
                   statepoint_seconds=timers["writing statepoints"],
                   process_wall_seconds=wall,
                   collision_events=collision_events,
                   cell_collision_events=cell_collision_events,
                   tally_shapes={key: list(value.shape) for key, value in tallies.items()},
                   tally_nonzero={key: int(np.count_nonzero(value)) for key, value in tallies.items()})
    (case / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{name}: {timers['transport']:.9f} s transport", flush=True)
    return receipt, tallies


def main():
    if OUT.exists():
        raise RuntimeError("Fresh output directory already exists")
    verify_inputs()
    OUT.mkdir(parents=True)
    receipts = {}
    arrays = {}
    for name, geometry, runtime in (("baseline", "custom", OLD),
                                    ("candidate", "custom", NEW),
                                    ("flat_ring", "fixed30", NEW)):
        receipts[name], arrays[name] = run_case(name, geometry, runtime)
    equal_bins = {key: bool(np.array_equal(arrays["baseline"][key], arrays["candidate"][key]))
                  for key in arrays["baseline"]}
    if not all(equal_bins.values()):
        raise RuntimeError(f"Before/after tally bins changed: {equal_bins}")
    summary = dict(disposition="COMPLETED_DIAGNOSTIC", receipts=receipts,
                   before_after_exact_raw_tally_bins=equal_bins,
                   candidate_to_baseline_transport=receipts["candidate"]["transport_seconds"] / receipts["baseline"]["transport_seconds"],
                   candidate_to_flat_ring_transport=receipts["candidate"]["transport_seconds"] / receipts["flat_ring"]["transport_seconds"],
                   old_runtime_is_retained_P00=True,
                   cold_CAD_build="UNKNOWN", checked_adapter="UNCHANGED",
                   local_mesh_bounds_cm=[[850, 0, -380], [950, 100, -280]],
                   collision_crossing_counts="UNKNOWN; not instrumented")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
