"""Exercise the raw-artifact checker and audit pilot material ownership.

Uses an existing completed run; never modifies its artifacts or launches transport.
"""
import argparse
import copy
import json
from pathlib import Path
import tempfile

import numpy as np
import openmc

from compare_proxy_transport import load, read, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.report / "plasma-native-1741"
    base = load(source / "receipt.json")
    tests = []
    with tempfile.TemporaryDirectory(prefix="stellarcsg-checker-") as temporary:
        work = Path(temporary)
        for file in source.iterdir():
            if file.is_file() and file.name not in ("receipt.json", "launch.json"):
                (work / file.name).symlink_to(file.resolve())
        mutations = ["runtime", "redistributed_bins", "seed_and_launch", "missing_statepoint",
                     "missing_MT444", "wrong_displacement_energy", "wrong_NRT", "wrong_uncertainty",
                     "nonzero_exit", "timeout", "unresolved_diagnostic"]
        for name in mutations:
            value = copy.deepcopy(base)
            launch = read(source / "launch.json")
            if name == "runtime":
                value["runtime_s"]["transport"] *= 2
            elif name == "redistributed_bins":
                batch = np.array(value["batch_scores"])
                # Preserve all totals and ownership closure while corrupting the spectrum.
                shift = batch[:, 8] / 2
                batch[:, 4] += shift
                batch[:, 8] -= shift
                value["batch_scores"] = batch.tolist()
                value["tally_means"]["1"] = batch[:, :24].mean(0).reshape(6, 1, 4).tolist()
            elif name == "seed_and_launch":
                value["seed"] += 1
                launch["seed"] += 1
            elif name == "missing_statepoint":
                value["statepoint_hashes"].pop("statepoint.01.h5")
            elif name == "missing_MT444":
                value["MT444_present"] = False
            elif name == "wrong_displacement_energy":
                value["displacement_energy_eV"] = 40000.
            elif name == "wrong_NRT":
                value["nrt_dpa_index_per_source"] *= 2
            elif name == "wrong_uncertainty":
                value["tally_std_dev"]["2"][0][0][0] += 1
            elif name == "nonzero_exit":
                value["exit_code"] = 1
            elif name == "timeout":
                value["timed_out"] = True
            elif name == "unresolved_diagnostic":
                (work / "stderr.txt").unlink()
                (work / "stderr.txt").write_text("unresolved geometry query\n")
            (work / "receipt.json").write_text(json.dumps(value))
            (work / "launch.json").write_text(json.dumps(launch))
            try:
                load(work / "receipt.json")
            except ValueError as error:
                tests.append(dict(control=name, state="REJECTED", reason=str(error)))
            else:
                raise AssertionError(f"forged receipt accepted: {name}")

    tracks = []
    for name in ("pilot-plasma-spline", "pilot-coil-spline", "pilot-coil-ordered"):
        files = sorted((args.report / name).glob("tracks.h5"))
        if len(files) != 1:
            raise ValueError(f"missing pilot tracks: {name}")
        count = 0
        for track in openmc.Tracks(files[0]):
            for particle in track.particle_tracks:
                states = particle.states
                cells, materials = states["cell_id"], states["material_id"]
                if not np.isin(cells, [1, 2, 3]).all():
                    raise ValueError("unexpected track cell")
                if not np.array_equal(materials == 1, cells == 2):
                    raise ValueError("track material/cell ownership mismatch")
                if not np.isin(materials, [-1, 1]).all():
                    raise ValueError("unexpected material")
                if not np.isfinite(states["E"]).all() or (states["E"] < 0).any():
                    raise ValueError("invalid track energy")
                count += len(states)
        if count == 0:
            raise ValueError("empty tracks")
        tracks.append(dict(run=name, sha256=sha(files[0]), states=count,
                           state="RECORDED_MATERIAL_OWNERSHIP_PASS"))
    result = dict(schema="stellarcsg.proxy-artifact-negative-controls/v1",
                  checker_sha256=sha(Path(__file__).with_name("compare_proxy_transport.py")),
                  audit_sha256=sha(__file__), baseline_receipt_sha256=sha(source / "receipt.json"),
                  controls=tests, tracks=tracks,
                  claim_boundary="Tampered receipts rejected against retained raw HDF5. Pilot recorded-state ownership only; not independent proof of every collision or arbitrary geometry.")
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
