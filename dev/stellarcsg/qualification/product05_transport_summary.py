"""Check cell/global track-length closure without requiring OpenMC Python."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import h5py
import numpy as np


def main():
    root = Path(__file__).resolve().parents[3]
    folder = root / "dev/stellarcsg/reports/product05/model-02"
    with h5py.File(folder / "xml/statepoint.1.h5") as state:
        per_cell = state["tallies/tally 1/results"][...,0].reshape(-1)
        global_flux = float(state["tallies/tally 2/results"][0,0,0])
        result = {"requested_histories": int(state["n_particles"][()]),
                  "current_batch": int(state["current_batch"][()]),
                  "n_batches": int(state["n_batches"][()]),
                  "n_realizations": int(state["n_realizations"][()]),
                  "leakage_fraction": float(state["global_tallies"][3,1]),
                  "runtime_seconds": {k: float(state["runtime"][k][()]) for k in state["runtime"]}}
    bins = list(map(int, ET.parse(folder / "xml/tallies.xml").findtext("filter/bins").split()))
    if len(bins) != len(per_cell) or len(set(bins)) != 18:
        raise RuntimeError("unexpected per-cell tally identity")
    delta = abs(float(per_cell.sum()) - global_flux)
    result.update({"cell_ids": bins, "cell_flux": per_cell.tolist(),
                   "global_flux": global_flux, "closure_absolute": delta,
                   "closure_relative": delta / abs(global_flux),
                   "positive_coil_bins": int(sum(value > 0 for cell,value in zip(bins,per_cell) if cell>=2000)),
                   "statepoint_sha256": hashlib.sha256((folder / "xml/statepoint.1.h5").read_bytes()).hexdigest(),
                   "claim": "one clipped exact-reference diagnostic; not periodic, not recovered throughput; no statistical uncertainty from one batch"})
    result["active_histories_per_second"] = result["requested_histories"] / result["runtime_seconds"]["active batches"]
    (folder / "closure.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if result["current_batch"] != result["n_batches"] or delta > 1e-10 * abs(global_flux):
        raise RuntimeError("completion or closure check failed")


if __name__ == "__main__":
    main()
