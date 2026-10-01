"""Adversarial controls for paired physics/result acceptance."""
import copy
import importlib.util
from pathlib import Path
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "qualification/compare_proxy_transport.py"
SPEC = importlib.util.spec_from_file_location("compare_proxy_transport", SOURCE)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def fixture():
    spectrum = np.arange(1., 25.).reshape(6, 4)
    row = np.concatenate((spectrum.ravel(), spectrum.sum(0), spectrum.sum(0)))
    batches = np.asarray([row * (1 + i / 100) for i in range(20)])
    mean = batches.mean(0)
    identities = dict(binary="a"*64, library="b"*64, source="c"*64, data="d"*64)
    inputs = {k: "e"*64 for k in ("geometry.xml", "materials.xml", "settings.xml", "tallies.xml")}
    return dict(state="OBSERVED_COMPLETE", exit_code=0, timed_out=False,
                forbidden_diagnostics=[], closure="PASS", family="coil",
                variant="spline", seed=1741, particles=10, batches=20,
                histories=200, threads=1, energy_bins_eV=CHECKER.ENERGY,
                scores=CHECKER.SCORES, estimator="tracklength", MT444_present=True,
                damage_model="NRT-test-index", volume_cm3=100., atoms=1e24,
                displacement_energy_eV=40., wall_s=1., runtime_s={"transport": .5},
                identities=identities, identities_after=copy.deepcopy(identities),
                input_hashes=inputs, inputs_after=copy.deepcopy(inputs),
                batch_scores=batches.tolist(), normalization="per source",
                settings_without_seed_sha256="9"*64,
                statepoint_hashes={f"statepoint.{i:02d}.h5": "f"*64 for i in range(1, 21)},
                tally_means={"1": mean[:24].reshape(6, 1, 4).tolist(),
                             "2": mean[24:28].reshape(1, 1, 4).tolist(),
                             "3": mean[28:].reshape(1, 1, 4).tolist()})


class TestProxyComparison(unittest.TestCase):
    def test_identical_pair_passes_observed_bins(self):
        a, b = fixture(), fixture()
        b["variant"] = "ordered"
        result = CHECKER.compare([(a, b)])
        self.assertTrue(result["recorded_batch_scores_agree"])
        self.assertTrue(result["all_bins_equivalent"])

    def test_swapped_conditions_rejected(self):
        for key, value in (("seed", 1751), ("volume_cm3", 101.),
                           ("atoms", 2e24), ("displacement_energy_eV", 41.)):
            a, b = fixture(), fixture()
            b[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECKER.compare([(a, b)])
        for key in ("source", "data", "binary"):
            a, b = fixture(), fixture()
            b["identities"][key] = b["identities_after"][key] = "0"*64
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECKER.compare([(a, b)])
        a, b = fixture(), fixture()
        b["input_hashes"]["materials.xml"] = b["inputs_after"]["materials.xml"] = "0"*64
        with self.assertRaises(ValueError):
            CHECKER.compare([(a, b)])

    def test_incomplete_nonfinite_wrong_units_rejected(self):
        mutations = [
            ("exit_code", 1), ("exit_code", False), ("timed_out", True),
            ("state", "RUNNING"), ("histories", 201), ("MT444_present", False),
            ("statepoint_hashes", {}), ("energy_bins_eV", [x / 1e6 for x in CHECKER.ENERGY]),
            ("batch_scores", [[float("nan")] * 32] * 20),
        ]
        for key, value in mutations:
            a = fixture()
            a[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                CHECKER.validate(a)

    def test_redistributed_bins_with_same_total_do_not_pass(self):
        a, b = fixture(), fixture()
        x = np.array(b["batch_scores"])
        x[:, 0] += x[:, 4] / 2
        x[:, 4] /= 2
        b["batch_scores"] = x.tolist()
        b["tally_means"]["1"] = x[:, :24].mean(0).reshape(6, 1, 4).tolist()
        result = CHECKER.compare([(a, b)])
        self.assertFalse(result["recorded_batch_scores_agree"])
        self.assertFalse(result["all_bins_equivalent"])

    def test_zero_spectrum_is_insufficient_not_equivalent(self):
        a = fixture()
        x = np.zeros((20, 32))
        a["batch_scores"] = x.tolist()
        a["tally_means"] = {"1": x[0, :24].reshape(6, 1, 4).tolist(),
                            "2": x[0, 24:28].reshape(1, 1, 4).tolist(),
                            "3": x[0, 28:].reshape(1, 1, 4).tolist()}
        result = CHECKER.compare([(a, copy.deepcopy(a))])
        self.assertFalse(result["all_bins_equivalent"])
        self.assertTrue(all(x["state"] == "INSUFFICIENT_COVERAGE" for x in result["bins"]))

    def test_duplicate_seed_pairs_rejected(self):
        pair = (fixture(), fixture())
        with self.assertRaises(ValueError):
            CHECKER.compare([pair, pair])

    def test_cross_seed_material_change_rejected(self):
        pairs = [(fixture(), fixture()), (fixture(), fixture())]
        for value in pairs[1]:
            value["seed"] = 2741
            value["input_hashes"]["materials.xml"] = value["inputs_after"]["materials.xml"] = "0"*64
        with self.assertRaises(ValueError):
            CHECKER.compare(pairs)

    def test_reversed_implementation_pair_keeps_strict_scope(self):
        a, b = fixture(), fixture()
        a["variant"], b["variant"] = "ordered", "spline"
        result = CHECKER.compare([(a, b)])
        self.assertEqual(result["comparison_scope"], "implementation")
        self.assertFalse(result["production_design_complete"])

    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):
            CHECKER.unique([("state", "PASS"), ("state", "FAIL")])


if __name__ == "__main__":
    unittest.main()
