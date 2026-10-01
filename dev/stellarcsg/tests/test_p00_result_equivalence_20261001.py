"""Audit retained P00 statepoints against the original and current methods.

Requires the local HDF5 statepoints named below; they are not source-controlled.
Run with ``python dev/stellarcsg/tests/test_p00_result_equivalence_20261001.py``.
"""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "dev/stellarcsg/reports"
ORIGINAL = REPORTS / "coil-profile-20260926/fixed-section-pair-010/custom"
DIAGNOSTIC = REPORTS / "p00-native-validation-20260930-03/transport"
SPEED = REPORTS / "p00-native-validation-20260930-05/speed"
PRODUCTION_IDS = (1, 2, 3)
SOURCE = ROOT.parent / ("stellarcsg-local-continuation-20260925/dev/stellarcsg/"
                        "reports/local-cont-20260925/p00-magnet-material-bank-02/"
                        "source.h5")
SOURCE_SHA256 = "d13553a31262d45067a8e096e73857d459054b482cf7bf0ccb52b927c611b442"
BASELINE_LIB_SHA256 = "fbc38dedc17e20342a56dd50e2d56f86330238dae00b95ab3e4602864967cba4"
CANDIDATE_LIB_SHA256 = "b83f361249cedcd1d67adc4829d0fc0222d8fcf11a7722f69e74f36f2ba25090"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_equal(left, right, label):
    if not np.array_equal(left, right):
        raise AssertionError(f"{label}: shape or raw sum/sum-square bins changed")


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def tally_contract(path):
    root = ET.parse(path).getroot()
    return {
        tag: [ET.canonicalize(ET.tostring(node, encoding="unicode"))
              for node in root.findall(tag)
              if int(node.attrib["id"]) in (1, 2, 3, 4)]
        for tag in ("filter", "tally")
    }


def load_case(folder, batch_count, seed, original=False, library_hash=None):
    statepoint_path = folder / f"statepoint.{batch_count}.h5"
    receipt = json.loads((folder / "receipt.json").read_text())
    expected_hash = receipt["statepoint_sha256"]
    xml_hashes = receipt["xml_hashes" if original else "xml_sha256"]
    for name, expected in xml_hashes.items():
        require(sha256(folder / name) == expected, f"{folder}: {name} hash")
    if library_hash:
        require(receipt["library_sha256"] == library_hash,
                f"{folder}: retained runtime identity")
    settings = ET.parse(folder / "settings.xml").getroot()
    require(settings.findtext("seed") == str(seed) and
            settings.findtext("run_mode") == "fixed source" and
            settings.find("source").attrib["file"].endswith(
                "p00-magnet-material-bank-02/source.h5"),
            f"{folder}: source/seed/mode settings")
    require(sha256(statepoint_path) == expected_hash,
            f"{folder}: statepoint hash")
    with h5py.File(statepoint_path) as statepoint:
        expected = dict(n_particles=1000, n_batches=batch_count,
                        current_batch=batch_count, n_realizations=batch_count)
        actual = {key: int(statepoint[key][()]) for key in expected}
        require(actual == expected, f"{folder}: incomplete history counters")
        require(int(statepoint["seed"][()]) == seed and
                statepoint["run_mode"][()].decode() == "fixed source" and
                statepoint["energy_mode"][()].decode() == "continuous-energy",
                f"{folder}: statepoint seed/run/energy mode")
        arrays = {identifier: np.asarray(
            statepoint[f"tallies/tally {identifier}/results"][()])
            for identifier in PRODUCTION_IDS}
    require(all(np.isfinite(array).all() for array in arrays.values()),
            f"{folder}: nonfinite production tally")
    return arrays, expected_hash


def audit():
    require(sha256(SOURCE) == SOURCE_SHA256, "frozen source bank hash")
    original_arrays, original_hash = load_case(ORIGINAL, 20, 1741, original=True)
    original_receipt = json.loads((ORIGINAL / "receipt.json").read_text())
    for identifier in PRODUCTION_IDS:
        saved = next(tally for tally in original_receipt["tallies"]
                     if tally["path"] == f"tallies/tally {identifier}/results")
        require_equal(original_arrays[identifier], np.asarray(saved["raw_values"]),
                      f"original receipt tally {identifier}")

    comparison = {"original_20k_statepoint_sha256": original_hash,
                  "production_tallies": list(PRODUCTION_IDS),
                  "exact_original_baseline_candidate_20k": True,
                  "exact_baseline_candidate_100k_by_seed": {}}
    for name in ("baseline", "candidate"):
        folder = DIAGNOSTIC / name
        arrays, _ = load_case(folder, 20, 1741,
                              library_hash=BASELINE_LIB_SHA256 if name ==
                              "baseline" else CANDIDATE_LIB_SHA256)
        for filename in ("geometry.xml", "materials.xml", "settings.xml"):
            require((ORIGINAL / filename).read_bytes() ==
                    (folder / filename).read_bytes(),
                    f"original versus {name} 20k {filename}")
        require(tally_contract(ORIGINAL / "tallies.xml") == tally_contract(
            folder / "tallies.xml"), "original production tally contract")
        for identifier in PRODUCTION_IDS:
            require_equal(original_arrays[identifier], arrays[identifier],
                          f"original versus {name} 20k tally {identifier}")

    for seed in (1741, 1742):
        folders = {name: SPEED / f"seed{seed}-{name}"
                   for name in ("baseline", "candidate")}
        before, before_hash = load_case(folders["baseline"], 100, seed,
                                        library_hash=BASELINE_LIB_SHA256)
        after, after_hash = load_case(folders["candidate"], 100, seed,
                                      library_hash=CANDIDATE_LIB_SHA256)
        for filename in ("geometry.xml", "materials.xml", "settings.xml",
                         "tallies.xml"):
            require((folders["baseline"] / filename).read_bytes() == (
                folders["candidate"] / filename).read_bytes(),
                f"seed {seed} 100k {filename}")
        for identifier in PRODUCTION_IDS:
            require_equal(before[identifier], after[identifier],
                          f"seed {seed} 100k tally {identifier}")
        comparison["exact_baseline_candidate_100k_by_seed"][str(seed)] = {
            "baseline_statepoint_sha256": before_hash,
            "candidate_statepoint_sha256": after_hash,
            "equal": True,
        }

    # An incorrect bin must make the equality gate fail.
    corrupted = original_arrays[1].copy()
    corrupted.flat[0] += 1.0
    try:
        require_equal(original_arrays[1], corrupted, "negative control")
    except AssertionError:
        comparison["negative_control_rejected"] = True
    else:
        raise AssertionError("negative control was accepted")
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    audit()
