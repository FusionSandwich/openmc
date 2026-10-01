"""Collect completed native workers after a floating-sum assertion stopped the driver."""

import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "dev/stellarcsg/reports/p00-native-validation-20260930-03/transport"
TALLY_IDS = (1, 2, 3, 301, 302, 303, 304)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect(name):
    case = OUT / name
    stdout = (case / "stdout.txt").read_text()
    stderr = (case / "stderr.txt").read_text()
    if "FIXED SOURCE TRANSPORT SIMULATION" not in stdout or "Leakage Fraction" not in stdout:
        raise RuntimeError(f"No native terminal result for {name}")
    if any(word in (stdout + stderr).lower() for word in
           ("lost particle", "unresolved", "fatal error")):
        raise RuntimeError(f"Tracking diagnostic for {name}")
    statepoint_path = case / "statepoint.20.h5"
    arrays = {}
    with h5py.File(statepoint_path) as statepoint:
        counters = {key: int(statepoint[key][()]) for key in
                    ("n_particles", "n_batches", "current_batch", "n_realizations")}
        if counters != dict(n_particles=1000, n_batches=20,
                            current_batch=20, n_realizations=20):
            raise RuntimeError(f"Incomplete histories for {name}")
        timers = {key: float(item[()]) for key, item in statepoint["runtime"].items()}
        for tally_id in TALLY_IDS:
            values = np.asarray(statepoint[f"tallies/tally {tally_id}/results"][()])
            if not np.isfinite(values).all():
                raise RuntimeError(f"Nonfinite tally {tally_id} for {name}")
            arrays[str(tally_id)] = values
    total = float(arrays["303"][..., 0].sum())
    partition = float(arrays["304"][..., 0].sum())
    # SCORE_EVENTS is one per collision; OpenMC normalizes each batch by its
    # 1000 source histories before accumulating the statepoint SUM column.
    count = round(1000 * total)
    if abs(total - partition) > 1e-10 or abs(1000 * total - count) > 1e-6:
        raise RuntimeError(f"Collision event normalization/partition differs for {name}")
    receipt = dict(name=name, completed_histories=20000, counters=counters,
                   timings_seconds=dict(initialization=timers["total initialization"],
                                        transport=timers["transport"],
                                        statepoint_output=timers["writing statepoints"]),
                   statepoint_sha256=sha(statepoint_path),
                   xml_sha256={p.name: sha(p) for p in case.glob("*.xml")},
                   collision_events=count,
                   local_mesh_nonzero_values=int(np.count_nonzero(arrays["301"])),
                   local_cell_mesh_nonzero_values=int(np.count_nonzero(arrays["302"])),
                   raw_tally_shapes={key: list(value.shape) for key, value in arrays.items()},
                   native_terminal=True,
                   native_exit_zero="observed by original driver before partition assertion")
    return receipt, arrays


def main():
    receipts, arrays = {}, {}
    for name in ("baseline", "candidate", "flat_ring"):
        receipts[name], arrays[name] = collect(name)
    before_after = {key: bool(np.array_equal(arrays["baseline"][key], arrays["candidate"][key]))
                    for key in arrays["baseline"]}
    if not all(before_after.values()):
        raise RuntimeError(f"Before/after raw bins differ: {before_after}")
    custom = receipts["candidate"]["timings_seconds"]["transport"]
    base = receipts["baseline"]["timings_seconds"]["transport"]
    ring = receipts["flat_ring"]["timings_seconds"]["transport"]
    summary = dict(disposition="COMPLETED_WORKERS_COLLECTED_AFTER_DRIVER_ASSERTION",
                   original_driver_failure="42.809 versus 42.809000000000005 collision-score floating summation",
                   worker_order=["baseline", "candidate", "flat_ring"],
                   receipts=receipts, exact_before_after_raw_tally_bins=before_after,
                   candidate_over_baseline_transport=custom / base,
                   candidate_over_flat_ring_transport=custom / ring,
                   diagnostic_gate_1_25=custom / ring <= 1.25,
                   speed_acceptance="UNQUALIFIED: collision event counters add profiling tally overhead; single ordered observation",
                   target_fidelity="derived seam-repaired facets only; continuous CAD, pack frame, distinct coil ownership unresolved",
                   actual_boundary_crossing_count="UNKNOWN")
    path = OUT / "RECOVERED_SUMMARY.json"
    if path.exists():
        raise RuntimeError("Collector receipt already exists")
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(dict(candidate_transport_s=custom, baseline_transport_s=base,
                          flat_ring_transport_s=ring, candidate_over_ring=custom / ring,
                          collision_events={name: receipt["collision_events"]
                                            for name, receipt in receipts.items()},
                          exact_bins=before_after), indent=2))


if __name__ == "__main__":
    main()
