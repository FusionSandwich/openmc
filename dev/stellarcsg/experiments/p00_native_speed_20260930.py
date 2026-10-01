"""Two bounded 100k matched P00 runtime pairs with frozen production tallies."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np

from p00_native_validate_20260930 import (ROOT, PREP, OLD, NEW, XS,
                                           child_limits, sha, verify_inputs)


OUT = ROOT / "dev/stellarcsg/reports/p00-native-validation-20260930-05/speed"


def set_workload(path, seed):
    tree = ET.parse(path)
    root = tree.getroot()
    root.find("batches").text = "100"
    root.find("state_point/batches").text = "100"
    root.find("seed").text = str(seed)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def run_case(seed, name, geometry, runtime):
    case = OUT / f"seed{seed}-{name}"
    case.mkdir()
    prepare_start = time.monotonic()
    for filename in ("geometry.xml", "materials.xml", "settings.xml", "tallies.xml"):
        shutil.copy2(PREP / geometry / filename, case / filename)
    set_workload(case / "settings.xml", seed)
    reused_preparation = time.monotonic() - prepare_start
    env = os.environ.copy()
    env.pop("LD_PRELOAD", None)
    env.update(OPENMC_CROSS_SECTIONS=str(XS), LD_LIBRARY_PATH=str(runtime / "lib"),
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    binary = runtime / "bin/openmc"
    loader = subprocess.run(["ldd", str(binary)], env=env, text=True,
                            capture_output=True, timeout=15)
    if loader.returncode or "not found" in loader.stdout or str(runtime / "lib/libopenmc.so") not in loader.stdout:
        raise RuntimeError(f"Native loader binding failed for {case}")
    (case / "loader.txt").write_text(loader.stdout)
    start = time.monotonic()
    with (case / "stdout.txt").open("w") as stdout, (case / "stderr.txt").open("w") as stderr:
        child = subprocess.Popen([str(binary)], cwd=case, env=env,
                                 stdout=stdout, stderr=stderr,
                                 preexec_fn=child_limits, start_new_session=True)
        try:
            code = child.wait(timeout=500)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            raise RuntimeError(f"Native timeout: {case}")
    wall = time.monotonic() - start
    if code != 0:
        raise RuntimeError(f"Native exit {code}: {case}")
    output = (case / "stdout.txt").read_text() + (case / "stderr.txt").read_text()
    if any(word in output.lower() for word in ("lost particle", "unresolved", "fatal error")):
        raise RuntimeError(f"Tracking diagnostic: {case}")
    arrays = {}
    with h5py.File(case / "statepoint.100.h5") as statepoint:
        counters = {key: int(statepoint[key][()]) for key in
                    ("n_particles", "n_batches", "current_batch", "n_realizations")}
        if counters != dict(n_particles=1000, n_batches=100,
                            current_batch=100, n_realizations=100):
            raise RuntimeError(f"Incomplete histories: {case}")
        timers = {key: float(item[()]) for key, item in statepoint["runtime"].items()}
        for tally_id in (1, 2, 3):
            array = np.asarray(statepoint[f"tallies/tally {tally_id}/results"][()])
            if not np.isfinite(array).all():
                raise RuntimeError(f"Nonfinite tally {tally_id}: {case}")
            arrays[str(tally_id)] = array
    receipt = dict(seed=seed, name=name, completed_histories=100000,
                   runtime=str(runtime), binary_sha256=sha(binary),
                   library_sha256=sha(runtime / "lib/libopenmc.so"),
                   xml_sha256={p.name: sha(p) for p in case.glob("*.xml")},
                   statepoint_sha256=sha(case / "statepoint.100.h5"),
                   counters=counters, preparation_seconds=reused_preparation,
                   initialization_seconds=timers["total initialization"],
                   transport_seconds=timers["transport"],
                   statepoint_seconds=timers["writing statepoints"],
                   process_wall_seconds=wall,
                   tally_shapes={key: list(value.shape) for key, value in arrays.items()},
                   tally_nonzero={key: int(np.count_nonzero(value))
                                  for key, value in arrays.items()})
    (case / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"seed{seed} {name}: {timers['transport']:.9f} s", flush=True)
    return receipt, arrays


def main():
    if OUT.exists():
        raise RuntimeError("Fresh speed output already exists")
    verify_inputs()
    OUT.mkdir(parents=True)
    receipts, arrays = {}, {}
    schedule = ((1741, "baseline", "custom", OLD),
                (1741, "candidate", "custom", NEW),
                (1741, "flat_ring", "fixed30", NEW),
                (1742, "flat_ring", "fixed30", NEW),
                (1742, "candidate", "custom", NEW),
                (1742, "baseline", "custom", OLD))
    for seed, name, geometry, runtime in schedule:
        receipt, data = run_case(seed, name, geometry, runtime)
        receipts[f"seed{seed}-{name}"] = receipt
        arrays[f"seed{seed}-{name}"] = data
    comparisons = []
    for seed in (1741, 1742):
        prefix = f"seed{seed}-"
        base, candidate, ring = (receipts[prefix + name]
                                 for name in ("baseline", "candidate", "flat_ring"))
        if any(base["xml_sha256"][item] != candidate["xml_sha256"][item]
               for item in ("geometry.xml", "materials.xml", "settings.xml", "tallies.xml")):
            raise RuntimeError(f"P00 before/after XML mismatch, seed {seed}")
        if any(candidate["xml_sha256"][item] != ring["xml_sha256"][item]
               for item in ("materials.xml", "settings.xml", "tallies.xml")):
            raise RuntimeError(f"P00/ring workload XML mismatch, seed {seed}")
        exact = {key: bool(np.array_equal(arrays[prefix + "baseline"][key],
                                          arrays[prefix + "candidate"][key]))
                 for key in arrays[prefix + "baseline"]}
        if not all(exact.values()):
            raise RuntimeError(f"P00 before/after tally bins differ, seed {seed}: {exact}")
        comparisons.append(dict(seed=seed, exact_before_after_bins=exact,
                                baseline_s=base["transport_seconds"],
                                candidate_s=candidate["transport_seconds"],
                                flat_ring_s=ring["transport_seconds"],
                                candidate_over_baseline=candidate["transport_seconds"] / base["transport_seconds"],
                                candidate_over_flat_ring=candidate["transport_seconds"] / ring["transport_seconds"]))
    summary = dict(disposition="COMPLETED_TWO_MATCHED_100K_PAIRS",
                   schedule=[f"seed{seed}-{name}" for seed, name, _, _ in schedule],
                   workers=receipts, comparisons=comparisons,
                   medians_seconds={name: float(np.median([receipts[f"seed{seed}-{name}"]["transport_seconds"]
                                                         for seed in (1741, 1742)]))
                                    for name in ("baseline", "candidate", "flat_ring")},
                   cold_geometry_build="UNKNOWN", instrumentation="NONE: frozen three production tallies",
                   source_occupancy="custom 0/18 source sites initially in material; flat ring 4/18",
                   continuous_CAD_and_distinct_physical_coil_ownership="UNRESOLVED")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
