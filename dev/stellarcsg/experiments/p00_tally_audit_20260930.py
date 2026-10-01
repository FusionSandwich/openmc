"""Independent per-cell/energy/local-bin accounting for the completed P00 run."""

import json
from pathlib import Path

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "dev/stellarcsg/reports/p00-native-validation-20260930-03/transport"


def raw(case, tally):
    with h5py.File(OUT / case / "statepoint.20.h5") as statepoint:
        return np.asarray(statepoint[f"tallies/tally {tally}/results"][()])


def within(left, right):
    return bool(np.allclose(left, right, rtol=1e-12, atol=1e-8))


def main():
    if (OUT / "TALLY_AUDIT.json").exists():
        raise RuntimeError("Audit receipt already exists")
    evidence = {}
    for case in ("baseline", "candidate"):
        cell_energy = raw(case, 1)[..., 0].reshape(18, 6, 4).sum(axis=1)
        cell_integral = raw(case, 2)[..., 0]
        material = raw(case, 3)[..., 0].reshape(4)
        mesh = raw(case, 301)[..., 0].reshape(64)
        cell_mesh = raw(case, 302)[..., 0].reshape(18, 64).sum(axis=0)
        energy_to_cell = within(cell_energy, cell_integral)
        cell_to_material = within(cell_integral.sum(axis=0), material)
        local_bin_partition = bool(np.all(cell_mesh <= mesh + 1e-10)
                                   and np.count_nonzero(cell_mesh) > 0)
        if not (energy_to_cell and cell_to_material and local_bin_partition):
            raise RuntimeError(f"Per-bin accounting failed: {case}")
        evidence[case] = dict(energy_to_cell_per_cell_per_score=energy_to_cell,
                              max_abs_energy_cell_difference=float(np.max(np.abs(cell_energy - cell_integral))),
                              cell_to_material_per_score=cell_to_material,
                              max_abs_cell_material_difference=float(np.max(np.abs(cell_integral.sum(axis=0) - material))),
                              local_mesh_cell_bin_partition=local_bin_partition,
                              local_mesh_nonzero_bins=int(np.count_nonzero(mesh)),
                              local_cell_mesh_nonzero_bins=int(np.count_nonzero(cell_mesh)),
                              local_mesh_total=float(mesh.sum()),
                              local_cell_mesh_total=float(cell_mesh.sum()))
    per_tally_identical = {str(tally): bool(np.array_equal(raw("baseline", tally),
                                                          raw("candidate", tally)))
                           for tally in (1, 2, 3, 301, 302, 303, 304)}
    if not all(per_tally_identical.values()):
        raise RuntimeError("Before/after local/raw tally bins differ")
    receipt = dict(disposition="PASS_REPRESENTED_SOLID_DIAGNOSTIC_ACCOUNTING",
                   evidence=evidence, before_after_exact_raw_bins=per_tally_identical,
                   scope="retained P00 facet fixture, seed 1741, 20k histories; no independent CAD or per-physical-coil proof",
                   transformed_overlapping_filters="NOT_TESTED; default assume_separate=false")
    (OUT / "TALLY_AUDIT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
