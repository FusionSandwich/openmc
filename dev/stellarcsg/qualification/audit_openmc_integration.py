"""Revalidate raw integration outputs and compare matched native/spline cases."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
import openmc


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(directory, wrapper):
    receipt = read(directory / "receipt.json")
    require(type(wrapper["exit_code"]) is int and wrapper["exit_code"] == 0
            and wrapper["timed_out"] is False and wrapper["failures"] == [], "failed wrapper")
    require(wrapper["receipt_sha256"] == sha(directory / "receipt.json"), "receipt hash mismatch")
    log = directory.parent / f"{directory.name}.txt"
    require(wrapper["log_sha256"] == sha(log), "log hash mismatch")
    require(not any(token in log.read_text().lower() for token in
                    ("lost particle", "could not be located", "unresolved", "traceback", "error:")), "failed diagnostics")
    require(receipt["state"] == "OBSERVED_INTEGRATION_PASS", "incomplete observation")
    for name, expected in receipt["output_hashes"].items():
        require(Path(name).name == name and sha(directory / name) == expected, "output mismatch")
    required = {"statepoint.5.h5", "summary.h5", "sampled-source.npy", "volume_1.h5",
                "local-flux.csv", "launch.json", "geometry.xml", "materials.xml", "settings.xml", "tallies.xml"}
    require(set(receipt["output_hashes"]) == required, "incomplete output set")
    require(set(receipt["xml_hashes"]) == {"geometry.xml", "materials.xml", "settings.xml", "tallies.xml"}, "incomplete XML set")
    require(all(receipt["output_hashes"][name] == value for name, value in receipt["xml_hashes"].items()), "XML hash maps disagree")
    launch = read(directory / "launch.json")
    for key in ("family", "variant", "source", "identities", "xml_hashes"):
        require(receipt[key] == launch[key], "launch identity mismatch")
    require(directory.name == f"{receipt['family']}-{receipt['variant']}-{receipt['source']}", "wrong run name")
    settings = ET.parse(directory / "settings.xml").getroot()
    source = settings.find("source")
    wanted = {"mesh": "mesh", "box": "independent", "file": "file"}[receipt["source"]]
    require(source is not None and source.get("type") == wanted, "wrong source implementation")
    if receipt["family"] == "plasma":
        require(source.findtext("constraints/domain_type") == "cell"
                and source.findtext("constraints/domain_ids") == "1"
                and source.findtext("constraints/rejection_strategy") == "resample", "source domain constraint missing")
    definitions = openmc.Tallies.from_xml(directory / "tallies.xml")
    by_id = {t.id: t for t in definitions}
    with openmc.StatePoint(directory / "statepoint.5.h5") as sp:
        require(sp.n_particles == launch["particles"] and sp.n_batches == 5
                and sp.n_realizations == 5 and sp.current_batch == 5
                and sp.seed == launch["seed"] == 917431, "raw statepoint mismatch")
        require(set(receipt["tallies"]) == {str(i) for i in sp.tallies}, "missing tally")
        for i, tally in sp.tallies.items():
            saved = receipt["tallies"][str(i)]
            require(tally.scores == saved["scores"] and tally.estimator == saved["estimator"]
                    and [type(f).__name__ for f in tally.filters] == saved["filters"], "tally metadata mismatch")
            definition = by_id[i]
            require(tally.nuclides == (definition.nuclides or ["total"])
                    and tally.scores == definition.scores and tally.estimator == definition.estimator
                    and len(tally.filters) == len(definition.filters), "tally definition mismatch")
            for actual, expected_filter in zip(tally.filters, definition.filters):
                require(type(actual) is type(expected_filter), "filter type mismatch")
                if isinstance(actual, openmc.EnergyFunctionFilter):
                    require(np.array_equal(actual.energy, expected_filter.energy)
                            and np.array_equal(actual.y, expected_filter.y), "response function mismatch")
                else:
                    require(np.array_equal(actual.bins, expected_filter.bins), "filter bins mismatch")
                if hasattr(actual, "mesh"):
                    require(type(actual.mesh) is type(expected_filter.mesh)
                            and actual.mesh.id == expected_filter.mesh.id, "mesh identity mismatch")
                    for attribute in ("dimension", "lower_left", "upper_right", "origin",
                                      "x_grid", "y_grid", "z_grid", "r_grid", "theta_grid", "phi_grid"):
                        if hasattr(expected_filter.mesh, attribute):
                            require(np.array_equal(getattr(actual.mesh, attribute),
                                                   getattr(expected_filter.mesh, attribute)), "mesh geometry mismatch")
            for name, actual in (("mean", tally.mean), ("std_dev", tally.std_dev)):
                require(np.isfinite(actual).all() and np.array_equal(actual, saved[name]), "raw tally data mismatch")
            require(np.abs(tally.mean).sum() > 0, f"tally {i} was not exercised")
        require(sp.runtime == receipt["runtime_s"], "runtime mismatch")
        surface = sp.summary.geometry.get_all_surfaces()[10]
        require(type(surface).__name__ == receipt["summary_surface"], "summary dispatch mismatch")
        means = {i: t.mean.sum(axis=(0, 1)) for i, t in sp.tallies.items()}
        for i in (2, 3, 5, 6, 7, 8, 9, 12, 18):
            delta = float(np.max(abs(means[i] - means[1])))
            require(np.allclose(means[i], means[1], rtol=2e-10, atol=1e-10)
                    and delta == receipt["closure_max_abs"][str(i)], "raw closure mismatch")
        require(np.allclose(means[4], means[17], rtol=2e-10, atol=1e-10), "local closure")
        require(np.allclose(means[16], 2 * means[1], rtol=2e-10, atol=1e-10), "response closure")
        if 19 in means:
            require(np.allclose(means[19], means[1], rtol=2e-10, atol=1e-10), "secondary birth mesh closure")
    sites = np.load(directory / "sampled-source.npy", allow_pickle=False)
    require(len(sites) == receipt["sampling"]["samples"] == 512, "sample count mismatch")
    require(receipt["sampling"]["sha256"] == sha(directory / "sampled-source.npy"), "sample hash mismatch")
    require(np.isfinite(sites["r"]).all() and np.all(sites["wgt"] == 1.), "source sample data")
    require(np.isfinite(sites["u"]).all() and np.allclose(np.linalg.norm(sites["u"], axis=1), 1., rtol=0, atol=2e-15), "source directions")
    if receipt["family"] == "plasma":
        r = sites["r"]
        require(np.all((np.hypot(r[:, 0], r[:, 1]) - 100.)**2 + r[:, 2]**2 < 400), "source outside analytic plasma")
    if receipt["source"] == "mesh":
        left = sites["r"][:, 0] < 100.
        require(np.all(sites["E"][left] == 2.45e6) and np.all(sites["E"][~left] == 14.1e6)
                and abs(left.mean() - .25) < .08, "conditional mesh-source spectrum")
    else:
        require(np.all(sites["E"] == 14.1e6), "source energy")
    volume = openmc.VolumeCalculation.from_hdf5(directory / "volume_1.h5").volumes[4]
    require([volume.n, volume.s] == receipt["local_volume_cm3"], "volume mismatch")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = read(args.report / "campaign-plan.json")
    wrappers = read(args.report / "campaign-progress.json")
    expected = [f"{family}-{variant}-{source}" for family, variant, source in plan["plan"]]
    require(len(expected) == len(set(expected)) == len(wrappers) == 6, "incomplete campaign")
    require([w["name"] for w in wrappers] == expected, "wrong campaign runs")
    receipts = {w["name"]: load(args.report / w["name"], w) for w in wrappers}
    worker_name = str(Path(__file__).with_name("check_openmc_integration.py").resolve())
    library_name = str(Path(__file__).resolve().parents[3] / "openmc/lib/libopenmc.so")
    for receipt in receipts.values():
        require(receipt["identities"][worker_name] == plan["worker_sha256"], "wrong campaign worker")
        if "library_sha256" in plan:
            require(receipt["identities"][library_name] == plan["library_sha256"], "wrong campaign library")
    pairs = []
    for family, source in (("plasma", "mesh"), ("plasma", "box"), ("coil", "file")):
        a, b = (receipts[f"{family}-{variant}-{source}"] for variant in ("native", "spline"))
        require(a["identities"] == b["identities"], "different implementation inputs")
        for name in ("materials.xml", "settings.xml", "tallies.xml"):
            require(a["xml_hashes"][name] == b["xml_hashes"][name], "different paired physics")
        require(a["sampling"]["sha256"] == b["sampling"]["sha256"], "different sampled source")
        comparisons = []
        for key, left in a["tallies"].items():
            right = b["tallies"][key]
            x, y = np.asarray(left["mean"]), np.asarray(right["mean"])
            require(x.shape == y.shape and left["filters"] == right["filters"]
                    and left["scores"] == right["scores"], "different tally layout")
            # Plasma is exactly the same surface. Coil is a bounded approximation.
            tolerance = (1e-8 + 1e-9 * np.maximum(abs(x), abs(y)) if family == "plasma"
                         else 1e-5 + 1e-4 * np.maximum(abs(x), abs(y)))
            close = bool(np.all(abs(x-y) <= tolerance))
            comparisons.append(dict(id=key, name=left["name"], bins=x.size,
                                    max_abs_difference=float(np.max(abs(x-y))),
                                    sampled_agreement=close))
        pairs.append(dict(family=family, source=source, sampled_source_identical=True,
                          native_local_volume_cm3=a["local_volume_cm3"],
                          spline_local_volume_cm3=b["local_volume_cm3"], tallies=comparisons))
    plasma_agreement = all(t["sampled_agreement"] for p in pairs if p["family"] == "plasma" for t in p["tallies"])
    result = dict(state="SAMPLED_INTEGRATION_AGREEMENT" if plasma_agreement else "SPATIAL_TALLY_REGRESSION_DETECTED",
                  raw_artifacts_valid=True, all_plasma_tallies_agree=plasma_agreement, runs=6, pairs=pairs,
                  audit_sha256=sha(__file__), receipt_sha256={n: sha(args.report/n/"receipt.json") for n in receipts},
                  claim_boundary="Matched finite proxy integration regression only; not universal filter/estimator, spectral or physical-source equivalence. Coil geometry is approximate; all sampling and statistics are limited.")
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({"state": result["state"], "runs": 6,
                      "tally_comparisons": sum(len(p["tallies"]) for p in pairs)}))


if __name__ == "__main__":
    main()
