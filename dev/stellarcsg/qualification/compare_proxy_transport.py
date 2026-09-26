"""Strict paired transport comparison; sparse bins never imply equivalence."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import openmc
from scipy.stats import t as student_t

ENERGY = [0., 1.e3, 1.e5, 1.e6, 5.e6, 1.e7, 14.2e6]
SCORES = ["flux", "total", "absorption", "damage-energy"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError("nonfinite JSON")))


def statepoint_name(index, batches):
    return f"statepoint.{index:0{len(str(batches))}d}.h5"


def validate(document):
    allowed = {"plasma": ("native", "spline"),
               "coil": ("native", "spline", "ordered", "annulus")}
    if document["family"] not in allowed or document["variant"] not in allowed[document["family"]]:
        raise ValueError("unknown family/variant")
    if (document["state"] != "OBSERVED_COMPLETE" or type(document["exit_code"]) is not int
            or document["exit_code"] != 0
            or document["timed_out"] or document["forbidden_diagnostics"]
            or document["closure"] != "PASS"):
        raise ValueError("execution incomplete or failed")
    for name in ("particles", "batches", "histories", "seed", "threads"):
        if type(document[name]) is not int or document[name] <= 0:
            raise ValueError("invalid execution count")
    if (document["histories"] != document["particles"] * document["batches"]
            or document["batches"] < 2 or document["threads"] != 1):
        raise ValueError("history/batch/thread mismatch")
    if (document["energy_bins_eV"] != ENERGY or document["scores"] != SCORES
            or document["estimator"] != "tracklength"
            or document["MT444_present"] is not True
            or document["damage_model"] != "NRT-test-index"):
        raise ValueError("score, energy units, estimator or damage model mismatch")
    for name in ("volume_cm3", "atoms", "displacement_energy_eV", "wall_s"):
        value = document[name]
        if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
            raise ValueError("invalid normalization/timing")
    if document["displacement_energy_eV"] != 40.:
        raise ValueError("changed test displacement energy")
    if (document["identities"] != document["identities_after"]
            or document["input_hashes"] != document["inputs_after"]):
        raise ValueError("execution provenance changed")
    batches = np.asarray(document["batch_scores"], dtype=float)
    if batches.shape != (document["batches"], 32) or not np.isfinite(batches).all():
        raise ValueError("missing or nonfinite batch bins")
    if (set(document["statepoint_hashes"]) !=
            {statepoint_name(i, document["batches"]) for i in range(1, document["batches"] + 1)}):
        raise ValueError("missing statepoints")
    if set(document["input_hashes"]) != {
            "geometry.xml", "materials.xml", "settings.xml", "tallies.xml"}:
        raise ValueError("missing XML hashes")
    expected = np.concatenate([np.array(document["tally_means"][str(i)]).ravel()
                               for i in (1, 2, 3)])
    if not np.allclose(batches.mean(axis=0), expected, rtol=1.e-11, atol=1.e-12):
        raise ValueError("batch scores do not reproduce tally means")
    for batch in batches:
        if (not np.allclose(batch[:24].reshape(6, 4).sum(axis=0), batch[24:28],
                            rtol=1.e-10, atol=1.e-10)
                or not np.allclose(batch[24:28], batch[28:], rtol=1.e-10, atol=1.e-10)):
            raise ValueError("spectral or material ownership closure fails")
    return batches


def load(path):
    path = Path(path)
    value = read(path)
    validate(value)
    for name, expected in {**value["input_hashes"], **value["statepoint_hashes"]}.items():
        target = path.parent / name
        if target.parent != path.parent or not target.is_file() or sha(target) != expected:
            raise ValueError(f"missing/changed run artifact: {name}")
    previous = None
    raw_batches = []
    for index in range(1, value["batches"] + 1):
        with h5py.File(path.parent / statepoint_name(index, value["batches"])) as statepoint:
            for key, expected in (("seed", value["seed"]),
                                  ("n_particles", value["particles"]),
                                  ("n_batches", value["batches"]),
                                  ("current_batch", index),
                                  ("n_realizations", index)):
                if int(statepoint[key][()]) != expected:
                    raise ValueError("raw statepoint identity mismatch")
            cumulative = np.concatenate([
                statepoint[f"tallies/tally {i}/results"][:, :, 0].ravel()
                for i in (1, 2, 3)])
            raw_batches.append(cumulative if previous is None else cumulative - previous)
            previous = cumulative
    if not np.array_equal(np.asarray(raw_batches), np.asarray(value["batch_scores"])):
        raise ValueError("receipt bins differ from raw statepoints")
    with openmc.StatePoint(path.parent / statepoint_name(value["batches"], value["batches"]),
                           autolink=False) as sp:
        for i in (1, 2, 3):
            tally = sp.get_tally(id=i)
            if tally.scores != SCORES or tally.estimator != "tracklength":
                raise ValueError("raw tally score/estimator mismatch")
            expected_types = (["CellFilter", "EnergyFilter"] if i == 1 else
                              ["CellFilter"] if i == 2 else ["MaterialFilter"])
            expected_bins = ([np.array([2]), np.column_stack((ENERGY[:-1], ENERGY[1:]))]
                             if i == 1 else [np.array([2 if i == 2 else 1])])
            if ([type(f).__name__ for f in tally.filters] != expected_types
                    or any(not np.array_equal(f.bins, bins)
                           for f, bins in zip(tally.filters, expected_bins))
                    or tally.nuclides != ["total"]):
                raise ValueError("raw tally filter/nuclide mismatch")
            for key, actual in (("tally_means", tally.mean),
                                ("tally_std_dev", tally.std_dev)):
                if (not np.isfinite(actual).all() or
                        not np.array_equal(actual, np.asarray(value[key][str(i)]))):
                    raise ValueError("raw tally values/uncertainties differ")
        if sp.runtime != value["runtime_s"]:
            raise ValueError("raw transport timing mismatch")
        actual_global = [dict(name=row["name"].decode(), mean=float(row["mean"]),
                              std_dev=float(row["std_dev"])) for row in sp.global_tallies]
        if actual_global != value["global_tallies"]:
            raise ValueError("raw global tally mismatch")
    damage = float(np.asarray(value["tally_means"]["2"]).ravel()[3])
    nrt = .8 * damage / (2 * value["displacement_energy_eV"] * value["atoms"])
    if not np.isclose(nrt, value["nrt_dpa_index_per_source"], rtol=1e-14, atol=0):
        raise ValueError("damage index inconsistent with tally/normalization")
    launch = read(path.parent / "launch.json")
    for key in ("identities", "input_hashes", "family", "variant", "seed",
                "histories", "particles", "batches", "energy_bins_eV", "scores",
                "MT444_present", "damage_model", "atoms", "volume_cm3"):
        if value[key] != launch[key]:
            raise ValueError("launch/receipt identity mismatch")
    for key in ("displacement_energy_eV", "threads", "estimator"):
        if value[key] != launch[key]:
            raise ValueError("launch/receipt normalization mismatch")
    settings = ET.parse(path.parent / "settings.xml").getroot()
    seed_node = settings.find("seed")
    if seed_node is None or int(seed_node.text) != value["seed"]:
        raise ValueError("settings seed mismatch")
    settings.remove(seed_node)
    value["settings_without_seed_sha256"] = hashlib.sha256(ET.tostring(settings)).hexdigest()
    diagnostics = ((path.parent / "stdout.txt").read_text()
                   + (path.parent / "stderr.txt").read_text()).lower()
    if any(token in diagnostics for token in
           ("could not be located", "lost particle", "unresolved", "error:", "terminate called")):
        raise ValueError("raw execution diagnostics contain a failure")
    surfaces = ET.parse(path.parent / "geometry.xml").getroot().findall("surface")
    kinds = {surface.get("type") for surface in surfaces}
    required = ("periodic-spline" if value["family"] == "plasma" else "swept-spline")
    if value["variant"] in ("spline", "ordered"):
        selected = [s for s in surfaces if s.get("type") == required]
        if len(selected) != 1:
            raise ValueError("wrong geometry implementation")
        if value["family"] == "coil":
            wanted = "true" if value["variant"] == "spline" else "false"
            if (selected[0].get("representation") != "exact_control_offset"
                    or selected[0].get("bernstein_prefix") != wanted):
                raise ValueError("wrong offset mode")
    elif required in kinds:
        raise ValueError("native receipt contains spline geometry")
    return value


def paired(left, right):
    a, b = validate(left), validate(right)
    keys = ("family", "seed", "particles", "batches", "histories", "threads",
            "identities", "energy_bins_eV", "scores", "estimator",
            "MT444_present", "damage_model", "volume_cm3", "atoms",
            "displacement_energy_eV", "normalization")
    for key in keys:
        if left[key] != right[key]:
            raise ValueError(f"unmatched condition: {key}")
    for name in ("materials.xml", "settings.xml", "tallies.xml"):
        if left["input_hashes"][name] != right["input_hashes"][name]:
            raise ValueError(f"unmatched physics input: {name}")
    return a, b


def compare(pairs):
    aa, bb, costs = [], [], []
    variants = None
    seeds = set()
    anchor = pairs[0][0]
    for left, right in pairs:
        a, b = paired(left, right)
        for key in ("family", "particles", "batches", "threads", "identities",
                    "volume_cm3", "atoms", "displacement_energy_eV",
                    "settings_without_seed_sha256"):
            if left[key] != anchor[key]:
                raise ValueError(f"heterogeneous production pair: {key}")
        for name in ("materials.xml", "tallies.xml"):
            if left["input_hashes"][name] != anchor["input_hashes"][name]:
                raise ValueError(f"heterogeneous physics input: {name}")
        identity = (left["family"], left["variant"], right["variant"])
        if variants is not None and identity != variants:
            raise ValueError("mixed comparison families/variants")
        variants = identity
        if left["seed"] in seeds:
            raise ValueError("duplicate seed pair")
        seeds.add(left["seed"])
        aa.append(a)
        bb.append(b)
        def transport_time(value):
            # The persisted OpenMC runtime metric excludes initialization.
            return float(value["runtime_s"]["transport"])
        ta, tb = transport_time(left), transport_time(right)
        if min(ta, tb) <= 0 or not np.isfinite([ta, tb]).all():
            raise ValueError("invalid transport time")
        costs.append(dict(seed=left["seed"], left_transport_s=ta,
                          right_transport_s=tb, right_relative_throughput=ta / tb))
    a, b = np.vstack(aa), np.vstack(bb)
    delta = b - a
    n = len(delta)
    # Simultaneous two-sided family-wise 95% paired intervals (Bonferroni).
    multiplier = float(student_t.ppf(1 - .05 / (2 * 32), n - 1))
    mean_a, mean_b = a.mean(axis=0), b.mean(axis=0)
    difference = delta.mean(axis=0)
    half = multiplier * delta.std(axis=0, ddof=1) / np.sqrt(n)
    observed = ((a != 0) | (b != 0)).sum(axis=0)
    bins = []
    for k in range(32):
        margin = .05 if k < 24 else .01
        bound = margin * abs(mean_a[k])
        enough = observed[k] >= 10 and mean_a[k] > 0
        equivalent = enough and abs(difference[k]) + half[k] <= bound
        bins.append(dict(index=k, score=SCORES[k % 4],
                         group="spectrum" if k < 24 else "integral" if k < 28 else "ownership",
                         energy_bin=k // 4 if k < 24 else None,
                         left_mean=float(mean_a[k]), right_mean=float(mean_b[k]),
                         paired_difference=float(difference[k]), simultaneous_halfwidth=float(half[k]),
                         observed_batches=int(observed[k]), relative_margin=margin,
                         state="EQUIVALENT_OBSERVED_BIN" if equivalent else
                         "INSUFFICIENT_COVERAGE" if not enough else "NOT_EQUIVALENT_OR_UNDERPOWERED"))
    sample_close = bool(np.all(np.abs(delta) <= 1.e-7 + 1.e-9 * np.maximum(abs(a), abs(b))))
    unordered = frozenset(variants[1:])
    exact_pair = ((variants[0] == "plasma" and unordered == {"native", "spline"})
                  or (variants[0] == "coil" and unordered == {"spline", "ordered"}))
    descriptive = "annulus" in variants or variants[1] == variants[2]
    production_design = len(pairs) == 3 and all(x["batches"] == 20 for pair in pairs for x in pair)
    all_bins = all(x["state"] == "EQUIVALENT_OBSERVED_BIN" for x in bins)
    qualified = (production_design and not descriptive and all_bins
                 and (sample_close if exact_pair else True))
    return dict(schema="stellarcsg.paired-proxy-comparison/v1", family=variants[0],
                left=variants[1], right=variants[2], pairs=len(pairs), paired_batches=n,
                recorded_batch_scores_agree=sample_close, bins=bins, timing=costs,
                mean_relative_throughput=float(np.mean([x["right_relative_throughput"] for x in costs])),
                all_bins_equivalent=all_bins,
                production_design_complete=production_design,
                comparison_scope="implementation" if exact_pair else
                "descriptive_shape_control" if descriptive else "geometry_approximation",
                full_spectrum_equivalence_qualified=qualified,
                flux_units="tracklength cm per source particle; divide by volume for volume-averaged flux",
                claim_boundary="Matched proxy observations only. Sparse bins remain unqualified. Coil damage index uses reference atoms; no device DPA/time or arbitrary-geometry qualification.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", nargs=2, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare([(load(a), load(b)) for a, b in args.pair])
    result["receipt_hashes"] = {p: sha(p) for pair in args.pair for p in pair}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("family", "left", "right", "pairs",
                     "recorded_batch_scores_agree", "all_bins_equivalent",
                     "mean_relative_throughput")}))


if __name__ == "__main__":
    main()
