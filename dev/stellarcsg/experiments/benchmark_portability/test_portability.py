"""Bounded single-CPU plumbing tests. No OpenMC, WISTELL, mesh or transport run."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import analytic_fixture as af
import gate_validator as gv
from make_fixture_plan import make_plan
import portable_bench as pb
import runtime_probe as rp

HERE = Path(__file__).resolve().parent


class PortabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="stellarcsg-portability-tests-")
        cls.root = Path(cls.temp.name)
        cls.serial = 0
        cls.plan_path = make_plan(cls.root / "base-plan", repetitions=1, lanes=1)
        cls.plan = pb.read_json(cls.plan_path)
        cls.receipt = pb.run_plan(cls.plan_path, cls.root / "base-run", enabled=True)
        cls.lane = cls.plan["lanes"][0]
        cls.queries = pb.load_bank(cls.plan_path.parent / "bank.json", cls.lane["geometry_domains"])
        cls.rows = [pb.strict_loads(x) for x in (cls.root / "base-run/candidate-0.jsonl").read_text().splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def folder(self):
        type(self).serial += 1
        return self.root / f"case-{self.serial:04d}"

    def raw_log(self, edit=None, mode="primary", lane=None):
        rows = copy.deepcopy(self.rows)
        if edit:
            edit(rows)
        path = self.folder().with_suffix(".jsonl")
        path.write_text("\n".join(json.dumps(r, allow_nan=False) for r in rows) + "\n")
        plan = copy.deepcopy(self.plan)
        plan["mode"] = mode
        return pb.analyze_log(path, self.queries, lane or self.lane, plan)

    def run_fault(self, fault, *, mode="primary", timeout=3):
        root = self.folder()
        plan_path = make_plan(root / "plan", repetitions=1, mode=mode, fault=fault, lanes=1)
        plan = pb.read_json(plan_path)
        plan["timeout_s"] = timeout
        plan_path.write_text(json.dumps(plan))
        receipt = pb.run_plan(plan_path, root / "run", enabled=True)
        return receipt, root / "run"

    def copy_receipt(self):
        path = self.folder()
        shutil.copytree(self.root / "base-run", path)
        return path

    def bank_edit(self, callback):
        _, bank = af.fixture_data()
        callback(bank)
        path = self.folder().with_suffix(".json")
        path.write_text(json.dumps(bank))
        return pb.load_bank(path, self.lane["geometry_domains"])

    def test_01_exact_rational_fixture_results(self):
        model, bank = af.fixture_data()
        for q in bank["queries"]:
            with self.subTest(query=q["id"]):
                result, distance, reason = af.solve(q, model)
                self.assertEqual((result, distance), (q["expected"]["result"], q["expected"]["distance_cm"]))
                self.assertIsNone(reason)

    def test_02_fixture_irrational_root_blocks_not_miss(self):
        model, bank = af.fixture_data()
        q = bank["queries"][2]
        q["origin"] = [-2, .5, 0]
        self.assertEqual(af.solve(q, model)[0], "UNRESOLVED")
        self.assertIsNotNone(af.solve(q, model)[2])

    def test_03_origin_contact_not_silently_suppressed(self):
        model, bank = af.fixture_data()
        self.assertEqual(af.solve(bank["queries"][5], model)[:2], ("HIT", 0))
        self.assertEqual(af.solve(bank["queries"][6], model)[:2], ("MISS", None))

    def test_04_even_root_is_hit(self):
        model, bank = af.fixture_data()
        self.assertEqual(af.solve(bank["queries"][3], model)[:2], ("HIT", 2))

    def test_05_direction_scaling_uses_distance_not_ray_parameter(self):
        model, bank = af.fixture_data()
        self.assertEqual(af.solve(bank["queries"][2], model), af.solve(bank["queries"][7], model))

    def test_06_duplicate_numeric_bank_tuple_rejected(self):
        def edit(b):
            q = copy.deepcopy(b["queries"][0]); q.update(id="disguised", category="other")
            q["origin"] = [-.25, -0.0, 0.0]
            b["queries"].append(q)
        with self.assertRaises(pb.Invalid):
            self.bank_edit(edit)

    def test_07_duplicate_id_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.bank_edit(lambda b: b["queries"][1].update(id=b["queries"][0]["id"]))

    def test_08_zero_direction_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.bank_edit(lambda b: b["queries"][0].update(direction=[0, 0, 0]))

    def test_09_unknown_geometry_domain_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.bank_edit(lambda b: b["queries"][0].update(geometry="unadmitted"))

    def test_10_nonfinite_json_rejected(self):
        for text in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}', '{"x":1,"x":2}'):
            with self.subTest(text=text), self.assertRaises(pb.Invalid):
                pb.strict_loads(text)

    def test_11_nonfinite_coordinates_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.bank_edit(lambda b: b["queries"][0].update(origin=[float("nan"), 0, 0]))

    def test_12_quantile_definition(self):
        self.assertEqual(pb.quantile([4, 1, 3, 2], .5), 2.5)
        self.assertAlmostEqual(pb.quantile([1, 2, 3, 4], .95), 3.85)
        self.assertAlmostEqual(pb.quantile([1, 2, 3, 4], .99), 3.97)
        self.assertEqual(pb.quantile([7], .99), 7)
        self.assertIsNone(pb.quantile([], .5))
        with self.assertRaises(pb.Invalid):
            pb.quantile([1], 1.1)

    def test_13_numeric_null_zero_boolean_contract(self):
        self.assertIsNone(pb.divide(None, 2))
        self.assertIsNone(pb.divide(1, 0))
        self.assertEqual(pb.divide(0, 2), 0)
        with self.assertRaises(pb.Invalid):
            pb.number(True, "time")
        with self.assertRaises(pb.Invalid):
            pb.number(-1, "time")

    def context(self, value):
        return {"value": value, "session_id": "synthetic-session", "environment_hash": "synthetic-env",
                "mode": "primary", "timing_origin": "synthetic", "bank_sha256": "same-bank",
                "model_sha256": "same-model", "query_class": "same-class", "metric_inputs_sha256": "same-queries"}

    def test_14_ratio_direction_distance_and_transport(self):
        self.assertEqual(pb.ratio_contract(self.context(20), self.context(10), "distance")["value"], 2)
        self.assertEqual(pb.ratio_contract(self.context(200), self.context(100), "transport")["value"], 2)
        self.assertEqual(pb.ratio_contract(self.context(200), self.context(100), "transport")["label"], "matched_throughput_ratio")

    def test_15_unlike_bank_only_sentinel(self):
        control = self.context(10); control["bank_sha256"] = "different-bank"
        r = pb.ratio_contract(self.context(20), control, "distance")
        self.assertEqual(r["value"], 2)
        self.assertEqual(r["label"], "sentinel_cost_ratio")

    def test_16_cross_session_environment_or_mode_ratio_refused(self):
        for key in ("session_id", "environment_hash", "mode", "timing_origin"):
            control = self.context(10); control[key] = "different"
            with self.subTest(key=key):
                self.assertIsNone(pb.ratio_contract(self.context(20), control, "distance")["value"])

    def test_17_diagnostics_never_primary_ratio(self):
        a, b = self.context(20), self.context(10)
        a["mode"] = b["mode"] = "diagnostic"
        self.assertIsNone(pb.ratio_contract(a, b, "distance")["value"])

    def test_18_log_input_hash_binding(self):
        with self.assertRaises(pb.Invalid):
            self.raw_log(lambda rows: rows[0].update(input_sha256="0" * 64))

    def test_19_log_duplicate_and_missing_query_rejected(self):
        for edit in (lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])), lambda rows: rows.pop(0)):
            with self.assertRaises(pb.Invalid):
                self.raw_log(edit)

    def test_20_summary_count_recomputed(self):
        with self.assertRaises(pb.Invalid):
            self.raw_log(lambda rows: rows[-1].update(blocked=1))

    def test_21_blocked_cannot_be_pass_or_miss(self):
        def edit(rows):
            rows[0]["candidate"].update(state="BLOCKED", result="MISS", distance_cm=None, reason="unresolved")
        with self.assertRaises(pb.Invalid):
            self.raw_log(edit)

    def test_22_blocked_reason_required(self):
        def edit(rows):
            rows[0]["candidate"].update(state="BLOCKED", result="UNRESOLVED", distance_cm=None, reason=None)
            rows[-1]["blocked"] = 1
        with self.assertRaises(pb.Invalid):
            self.raw_log(edit)

    def test_23_non_hit_distance_must_be_null(self):
        with self.assertRaises(pb.Invalid):
            self.raw_log(lambda rows: rows[0]["candidate"].update(result="MISS", distance_cm=1))

    def test_24_exact_reference_candidate_survives_optional_skipped(self):
        lane = copy.deepcopy(self.lane)
        lane.update(authority="exact_reference", authority_evidence="Synthetic adapter test; not an audited native oracle")
        r = self.raw_log(lane=lane)
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["candidate_authority"], "exact_reference")
        self.assertEqual(r["queries"][0]["reference"]["state"], "SKIPPED")
        self.assertEqual(r["authority_verification"], "DECLARED_NOT_INDEPENDENTLY_CERTIFIED")

    def test_25_sampled_reference_never_completeness_certificate(self):
        r = self.raw_log()
        self.assertEqual(r["correctness_claim"], "FINITE_BANK_ONLY_NOT_COMPLETENESS")
        self.assertFalse(self.receipt["summary"]["statistics"]["candidate"]["completeness_certificate"])

    def test_26_primary_counter_contamination_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.raw_log(lambda rows: rows[0]["counters"].update(candidate_count=1))

    def test_27_primary_reference_calls_rejected(self):
        with self.assertRaises(pb.Invalid):
            self.raw_log(lambda rows: rows[0]["reference"].update(state="AGREE"))

    def test_28_negative_or_boolean_timings_rejected(self):
        for bad in (-1, True):
            with self.subTest(value=bad), self.assertRaises(pb.Invalid):
                self.raw_log(lambda rows: rows[0]["timing_ns"].update(distance=bad))

    def test_29_duplicate_point_bank_cannot_claim_unique_timings(self):
        r = self.raw_log(lambda rows: rows[1]["points"].update(classification=rows[0]["points"]["classification"]))
        # First two queries share slab geometry; repeating the point is a true duplicate.
        a = copy.deepcopy(self.receipt["attempts"][0]); a["analysis"] = r
        stats = pb.lane_statistics(self.lane, [a], self.queries, 1)
        self.assertIsNone(stats["metrics"]["classification"]["cold_bank_ns_per_query"])
        self.assertIsNotNone(stats["metrics"]["distance"]["cold_bank_ns_per_query"])

    def test_30_cold_bank_mean_median_distinct_from_query_median(self):
        root = self.folder()
        pp = make_plan(root / "plan", repetitions=3, lanes=1)
        r = pb.run_plan(pp, root / "run", enabled=True)
        m = r["summary"]["statistics"]["candidate"]["metrics"]["distance"]
        self.assertEqual(m["cold_bank_ns_per_query"], 99)
        self.assertEqual(m["bank_means_by_repeat"], {"0": 90, "1": 99, "2": 108})
        self.assertEqual(m["bank_mean_repeat_variability"]["sample_sd"], 9)
        self.assertEqual(m["available_queries_by_repeat"], [8, 8, 8])

    def test_31_default_off_no_output_or_execution(self):
        out = self.folder()
        with self.assertRaises(pb.Invalid):
            pb.run_plan(self.plan_path, out)
        self.assertFalse(out.exists())

    def test_32_duplicate_lane_labels_fail_preflight(self):
        p = copy.deepcopy(self.plan)
        p["lanes"].append(copy.deepcopy(p["lanes"][0]))
        with self.assertRaises(pb.Invalid):
            pb.check_plan(p)

    def test_33_invalid_plan_parameters(self):
        for key, value in (("repetitions", 0), ("repetitions", True), ("timeout_s", 0),
                           ("mode", "instrumented-primary"), ("max_log_bytes", 4 * 1024**2)):
            p = copy.deepcopy(self.plan); p[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(pb.Invalid):
                pb.check_plan(p)

    def test_34_plan_hash_mismatch_prevents_launch(self):
        p = copy.deepcopy(self.plan)
        p["artifacts"]["bank"]["sha256"] = "0" * 64
        with self.assertRaises(pb.Invalid):
            pb.validate_artifacts(p, self.plan_path.parent)

    def test_35_missing_executable_prevents_launch(self):
        lane = copy.deepcopy(self.lane); lane["command"] = ["nonexistent-stellarcsg-test-command"]
        with self.assertRaises(pb.Invalid):
            pb.expand_command(lane, {}, 0)

    def test_36_output_collision_refused(self):
        with self.assertRaises(FileExistsError):
            pb.run_plan(self.plan_path, self.root / "base-run", enabled=True)

    def test_37_child_exit7_not_hidden(self):
        r, out = self.run_fault("exit7")
        self.assertEqual(r["attempts"][0]["exit_code"], 7)
        self.assertEqual(r["summary"]["execution_status"], "FAIL")
        self.assertIsNone(r["summary"]["statistics"]["candidate"]["metrics"]["distance"]["cold_bank_ns_per_query"])
        self.assertEqual(pb.validate_receipt(out / "receipt.json")["execution_status"], "FAIL")

    def test_38_child_zero_but_failed_status_not_hidden(self):
        r, _ = self.run_fault("fail")
        self.assertEqual(r["attempts"][0]["exit_code"], 0)
        self.assertEqual(r["summary"]["execution_status"], "FAIL")

    def test_39_child_zero_but_blocked_not_hidden(self):
        r, _ = self.run_fault("blocked")
        self.assertEqual(r["attempts"][0]["exit_code"], 0)
        self.assertEqual(r["summary"]["execution_status"], "BLOCKED")
        query = next(q for q in r["attempts"][0]["analysis"]["queries"] if q["id"] == "near-entry")
        self.assertEqual(query["candidate"]["reason"], "EARLIER_PREFIX_UNRESOLVED_TEST_FIXTURE")
        self.assertEqual(query["candidate"]["result"], "UNRESOLVED")

    def test_40_malformed_logs_and_summary_are_failures(self):
        for fault in ("malformed", "nan", "wrong_summary", "missing_record", "duplicate_id"):
            with self.subTest(fault=fault):
                r, out = self.run_fault(fault)
                self.assertEqual(r["summary"]["execution_status"], "FAIL")
                self.assertTrue(r["attempts"][0]["validation_errors"])
                self.assertEqual(pb.validate_receipt(out / "receipt.json")["receipt_integrity"], "VALID")

    def test_41_wrong_fixture_result_not_hidden_by_pass(self):
        r, _ = self.run_fault("wrong_result")
        self.assertEqual(r["attempts"][0]["analysis"]["counts"]["fixture_mismatches"], 1)
        self.assertEqual(r["summary"]["execution_status"], "FAIL")

    def test_42_partial_timing_no_survivor_average(self):
        r, _ = self.run_fault("null_timing")
        metric = r["summary"]["statistics"]["candidate"]["metrics"]["distance"]
        self.assertIsNone(metric["cold_bank_ns_per_query"])
        self.assertIsNone(metric["pooled_per_query_ns"]["p95"])
        self.assertEqual(metric["available_queries_by_repeat"], [7])

    def test_43_timeout_is_preserved(self):
        r, out = self.run_fault("timeout", timeout=.1)
        self.assertEqual(r["attempts"][0]["termination"], "TIMEOUT")
        self.assertNotEqual(r["attempts"][0]["exit_code"], 0)
        self.assertEqual(pb.validate_receipt(out / "receipt.json")["execution_status"], "FAIL")

    def test_44_signal_exit_preserved(self):
        r, _ = self.run_fault("signal")
        self.assertEqual(r["attempts"][0]["exit_code"], -15)
        self.assertEqual(r["summary"]["execution_status"], "FAIL")

    def test_45_output_limit_is_bounded_and_preserved(self):
        r, _ = self.run_fault("flood")
        a = r["attempts"][0]
        self.assertEqual(a["termination"], "OUTPUT_LIMIT")
        self.assertLessEqual(a["stdout"]["bytes"], 65536)
        self.assertEqual(r["summary"]["execution_status"], "FAIL")

    def test_46_grandchild_cleanup_after_parent_exit(self):
        r, out = self.run_fault("spawn_grandchild")
        self.assertEqual(r["summary"]["execution_status"], "PASS")
        pid = int((out / "descendant.pid").read_text())
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists():
            self.assertIn(stat.read_text().rsplit(")", 1)[1].split()[0], ("Z", "X"))

    def test_47_spawn_error_is_not_success(self):
        out = self.folder(); out.mkdir()
        with patch.object(pb.subprocess, "Popen", side_effect=PermissionError("test denial")):
            a = pb.execute_child([sys.executable], out, "denied", self.plan, "synthetic")
        self.assertEqual(a["termination"], "SPAWN_ERROR")
        self.assertIsNone(a["exit_code"])

    def test_48_diagnostics_counts_and_time_fractions(self):
        r, _ = self.run_fault("none", mode="diagnostic")
        d = r["summary"]["statistics"]["candidate"]["diagnostics"]
        self.assertEqual(d["candidate_count"], 36)
        self.assertEqual(d["recovery_query_fraction"], 3/8)
        self.assertAlmostEqual(d["recovery_time_fraction"], 24/360)
        self.assertEqual(d["fallback_query_fraction"], 1/8)
        self.assertAlmostEqual(d["fallback_time_fraction"], 40/360)
        self.assertEqual(d["allocations"], 0)
        self.assertIsNone(self.receipt["summary"]["statistics"]["candidate"]["diagnostics"]["allocations"])

    def test_49_reference_block_reason_preserved_separately(self):
        r, _ = self.run_fault("reference_blocked", mode="diagnostic")
        a = r["attempts"][0]["analysis"]
        self.assertEqual(a["counts"]["reference_blocked"], 1)
        self.assertEqual(a["counts"]["blocked"], 0)
        self.assertEqual(a["comparison_status"], "REFERENCE_BLOCKED")
        self.assertEqual(r["summary"]["execution_status"], "BLOCKED")

    def test_50_sampled_disagreement_not_erased(self):
        r, _ = self.run_fault("reference_disagreement", mode="diagnostic")
        a = r["attempts"][0]["analysis"]
        self.assertEqual(a["comparison_status"], "DISAGREEMENTS")
        self.assertEqual(a["counts"]["reference_disagreements"], 1)
        self.assertEqual(a["counts"]["candidate_failures"], 0)

    def test_51_recovery_time_larger_than_distance_rejected(self):
        r, out = self.run_fault("none", mode="diagnostic")
        rows = [json.loads(x) for x in (out / "candidate-0.jsonl").read_text().splitlines()]
        rows[0]["recovery_ns"] = rows[0]["timing_ns"]["distance"] + 1
        log = self.folder().with_suffix(".jsonl")
        log.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        p = copy.deepcopy(self.plan); p["mode"] = "diagnostic"
        with self.assertRaises(pb.Invalid):
            pb.analyze_log(log, self.queries, self.lane, p)

    def test_52_valid_receipt_and_missing_native_control(self):
        v = pb.validate_receipt(self.root / "base-run/receipt.json")
        self.assertEqual(v["receipt_integrity"], "VALID")
        self.assertEqual(v["performance_status"], "INCOMPLETE")
        for metric in pb.METRICS:
            self.assertIsNone(self.receipt["summary"]["ratios"]["candidate"]["native_ztorus"][metric]["value"])
        self.assertIsNone(self.receipt["summary"]["ratios"]["candidate"]["native_ztorus"]["transport"]["value"])

    def test_53_receipt_can_move_without_desktop_paths(self):
        copied = self.copy_receipt()
        self.assertEqual(pb.validate_receipt(copied / "receipt.json")["receipt_integrity"], "VALID")

    def test_54_log_tamper_rejected(self):
        copied = self.copy_receipt()
        p = copied / "candidate-0.jsonl"; p.write_text(p.read_text() + "\n")
        with self.assertRaises(pb.Invalid):
            pb.validate_receipt(copied / "receipt.json")

    def test_55_summary_metric_tamper_recomputed(self):
        copied = self.copy_receipt()
        p = copied / "receipt.json"; r = pb.read_json(p)
        r["summary"]["statistics"]["candidate"]["metrics"]["distance"]["cold_bank_ns_per_query"] = 1
        p.write_text(json.dumps(r))
        with self.assertRaises(pb.Invalid):
            pb.validate_receipt(p)

    def test_56_session_tamper_rejected(self):
        copied = self.copy_receipt()
        p = copied / "receipt.json"; r = pb.read_json(p); r["session_id"] = "other-session"
        p.write_text(json.dumps(r))
        with self.assertRaises(pb.Invalid):
            pb.validate_receipt(p)

    def test_57_input_mutation_detected(self):
        r, _ = self.run_fault("mutate_input")
        self.assertEqual(r["summary"]["execution_status"], "FAIL")
        self.assertIn("artifact hash mismatch", r["attempts"][0]["validation_errors"][0])

    def test_58_receipt_path_escape_rejected(self):
        with self.assertRaises(pb.Invalid):
            pb.inside(self.root, "../outside")
        with self.assertRaises(pb.Invalid):
            pb.inside(self.root, "/etc/passwd")

    def test_59_old_guardrail_not_applied_to_synthetic_times(self):
        root = self.folder(); pp = make_plan(root / "plan", repetitions=3, lanes=3)
        r = pb.run_plan(pp, root / "run", enabled=True)
        ratio = r["summary"]["ratios"]["candidate"]["old_fast"]["distance"]
        self.assertEqual(ratio["value"], 2)
        self.assertEqual(ratio["paired_repeat_ratios"], [2, 2, 2])
        self.assertEqual(r["summary"]["ratios"]["candidate"]["old_fast_guardrail"], "NOT_EVALUATED")
        self.assertEqual(r["summary"]["statistics"]["exact_reference_fixture"]["authority"], "analytic_exact")

    def test_60_mock_named_native_is_not_native(self):
        plan = copy.deepcopy(self.plan)
        lane = copy.deepcopy(self.lane); lane.update(name="native_ztorus", role="native_ztorus")
        plan["lanes"].append(lane)
        pb.check_plan(plan)
        attempts = copy.deepcopy(self.receipt["attempts"])
        fake = copy.deepcopy(attempts[0]); fake["lane"] = "native_ztorus"; attempts.append(fake)
        r = pb.summarize(plan, attempts, {"candidate": self.queries, "native_ztorus": self.queries}, "env", "session")
        self.assertIsNone(r["ratios"]["candidate"]["native_ztorus"]["distance"]["value"])
        self.assertEqual(r["performance_status"], "INCOMPLETE")

    def test_61_runtime_filename_and_flags_are_not_proof(self):
        root = self.folder(); root.mkdir()
        fake = root / "openmc-DAGMC-DOUBLE_DOWN-embree"
        fake.write_text("OPENMC_USE_DAGMC=ON DOUBLE_DOWN=ON")
        cache = root / "CMakeCache.txt"
        cache.write_text("DOUBLE_DOWN:BOOL=ON\nOPENMC_USE_DAGMC:BOOL=ON\n")
        r = rp.collect(fake, records=[cache])
        self.assertEqual(r["backend_status"], "UNVERIFIED")
        self.assertEqual(r["double_down_embree"], "UNVERIFIED")
        self.assertEqual(r["binary"]["format"], "NOT_ELF")

    def test_62_read_only_probe_does_not_invoke_target(self):
        root = self.folder(); root.mkdir()
        marker = root / "SHOULD_NOT_EXIST"
        target = root / "openmc"
        target.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        target.chmod(0o755)
        rp.collect(target)
        self.assertFalse(marker.exists())

    def test_63_read_only_real_local_elf_and_process(self):
        r = rp.collect(Path(sys.executable), pid=os.getpid())
        self.assertEqual(r["backend_status"], "UNVERIFIED")
        self.assertEqual(r["binary"]["sha256"], pb.digest(sys.executable))
        self.assertIn(r["process"]["status"], ("LOCAL_MAPPINGS_OBSERVED", "UNVERIFIED"))
        self.assertEqual(r["bateman_live_linkage"], "UNKNOWN_NOT_CONTACTED")

    def test_64_all_final_transport_gates_remain_blocked(self):
        r = gv.check_manifest(HERE / "matched_readiness.blocked.json")
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertEqual(len(r["blocked"]), 12)
        self.assertEqual(r["execution"], "NOT_IMPLEMENTED_NO_TRANSPORT_LAUNCH")

    def test_65_gate_pass_without_evidence_rejected(self):
        m = pb.read_json(HERE / "matched_readiness.blocked.json")
        m["gates"][gv.GATES[0]]["state"] = "PASS"
        p = self.folder().with_suffix(".json"); p.write_text(json.dumps(m))
        with self.assertRaises(pb.Invalid):
            gv.check_manifest(p)

    def test_66_cli_nonzero_for_failed_child_and_strict_missing_control(self):
        root = self.folder(); pp = make_plan(root / "plan", repetitions=1, fault="exit7", lanes=1)
        result = subprocess.run([sys.executable, str(HERE / "portable_bench.py"), "run", "--enable-experiment",
                                 "--plan", str(pp), "--output", str(root / "run")], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        root = self.folder(); pp = make_plan(root / "plan", repetitions=1, lanes=1)
        result = subprocess.run([sys.executable, str(HERE / "portable_bench.py"), "run", "--enable-experiment",
                                 "--require-native-control", "--plan", str(pp), "--output", str(root / "run")],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3, result.stderr)


    def legacy_log(self, edit=None, mode="primary", authority="exact_reference"):
        rows = []
        qmap = {q["id"]: q for q in self.queries}
        for r in self.rows[:-1]:
            q, c = qmap[r["id"]], r["candidate"]
            rows.append({"kind": "query", "id": r["id"], "category": q["category"], "heldout": False,
                         "coefficient_hash": "fnv-not-cryptographic", "source_sha256": "", "expected": "reference_required",
                         "candidate_found": c["result"] == "HIT", "candidate_distance": c["distance_cm"],
                         "candidate_ok": c["state"] == "PASS", "candidate_state": c["state"], "state": c["state"],
                         "candidate_distance_ns": r["timing_ns"]["distance"], "evaluate_ns": r["timing_ns"]["classification"],
                         "normal_ns": r["timing_ns"]["normal"], "telemetry_state": "PASS",
                         "reference_available": False, "reference_state": "SKIPPED", "reference_found": False,
                         "reference_distance": None, "reference_distance_ns": None, "reference_agrees": None,
                         "counter_distance_calls": None, "counter_cache_hits": None, "counter_cache_misses": None,
                         "candidate_spans": None, "candidate_newton": None, "candidate_subdivision": None})
        rows.append({"kind": "summary", "query_count": len(self.queries), "candidate_failures": 0,
                     "candidate_nearest_failures": 0, "reference_disagreements": 0, "blocked": 0,
                     "cache_policy": "unique_queries_fresh_process", "claim": "bounded_replay_not_completeness"})
        if edit:
            edit(rows)
        path = self.folder().with_suffix(".jsonl")
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        lane = copy.deepcopy(self.lane); lane.update(parser="recovery04", authority=authority)
        plan = copy.deepcopy(self.plan); plan["mode"] = mode
        return pb.analyze_log(path, self.queries, lane, plan)

    def test_67_actual_legacy_schema_preserves_exact_candidate_with_skipped(self):
        r = self.legacy_log()
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["candidate_authority"], "exact_reference")
        self.assertEqual(r["queries"][0]["reference"]["strength"], "sampled")
        self.assertEqual(r["queries"][0]["reference"]["state"], "SKIPPED")
        self.assertIsNone(r["summary"]["setup_ns"])
        self.assertIsNone(r["queries"][0]["points"]["normal"])

    def test_68_actual_legacy_compact_geometry_hash_block_preserved(self):
        def edit(rows):
            rows[0] = {"kind": "query", "id": rows[0]["id"], "state": "BLOCKED",
                       "reason": "surface_unavailable_or_coefficient_or_fixture_hash_mismatch"}
            rows[-1]["blocked"] = 1
        r = self.legacy_log(edit)
        q = next(q for q in r["queries"] if q["id"] == "near-entry")
        self.assertEqual(q["candidate"]["result"], "UNRESOLVED")
        self.assertEqual(q["candidate"]["reason"], "surface_unavailable_or_coefficient_or_fixture_hash_mismatch")
        self.assertIsNone(q["timing_ns"]["distance"])
        self.assertEqual(r["status"], "BLOCKED")

    def test_69_legacy_reference_block_preserves_reason(self):
        def edit(rows):
            rows[0].update(reference_available=True, reference_state="BLOCKED",
                           reference_error="whole_span_admission_unresolved")
        r = self.legacy_log(edit, mode="diagnostic")
        self.assertEqual(r["counts"]["reference_blocked"], 1)
        self.assertEqual(r["comparison_status"], "REFERENCE_BLOCKED")
        self.assertEqual(r["status"], "BLOCKED")

    def test_70_legacy_reference_flags_cannot_contradict_skipped(self):
        for edit in (lambda rows: rows[0].update(reference_available=True),
                     lambda rows: rows[0].update(reference_distance_ns=1),
                     lambda rows: rows[0].pop("candidate_distance_ns")):
            with self.assertRaises(pb.Invalid):
                self.legacy_log(edit)

    def test_71_csv_numeric_bank_uniqueness(self):
        import csv
        path = self.folder().with_suffix(".csv")
        def write(duplicate):
            with path.open("w", newline="") as stream:
                w = csv.writer(stream)
                w.writerow(["id", "geometry", "coefficient_hash", "source_sha256", "category", "heldout", "expected",
                            "expected_distance", "group", "ox", "oy", "oz", "dx", "dy", "dz"])
                for q in self.queries:
                    category = "coincident_in" if q["coincident"] else q["category"]
                    w.writerow([q["id"], q["geometry"], "fnv-test", "", category, 0, "reference_required", "", "", *q["origin"], *q["direction"]])
                if duplicate:
                    q = self.queries[0]
                    w.writerow(["duplicate", q["geometry"], "fnv-test", "", "other_label", 1, "reference_required", "", "", *q["origin"], *q["direction"]])
        write(False)
        self.assertEqual(len(pb.load_bank(path, self.lane["geometry_domains"])), 8)
        write(True)
        with self.assertRaises(pb.Invalid):
            pb.load_bank(path, self.lane["geometry_domains"])

    def test_72_recorded_command_arguments_bound_to_plan(self):
        copied = self.copy_receipt()
        p = copied / "receipt.json"; r = pb.read_json(p)
        r["attempts"][0]["command"][-1] = "hidden-change"
        (copied / "attempt-0000.json").write_text(json.dumps(r["attempts"][0]))
        p.write_text(json.dumps(r))
        with self.assertRaises(pb.Invalid):
            pb.validate_receipt(p)

    def test_73_native_provenance_requires_structured_bound_review(self):
        root = self.folder(); pp = make_plan(root / "plan", repetitions=1, lanes=1)
        plan = pb.read_json(pp)
        record = pp.parent / "empty-review.json"; record.write_text("{}")
        plan["artifacts"]["review"] = {"path": record.name, "sha256": pb.digest(record)}
        lane = plan["lanes"][0]
        lane["native_provenance"] = {"review_record_artifact": "review", "binary_sha256": "0"*64,
                                     "implementation": "openmc::ZTorus", "review_status": "SOURCE_AND_BINARY_REVIEWED"}
        with self.assertRaises(pb.Invalid):
            pb.validate_artifacts(plan, pp.parent)

    def test_74_oversized_planned_output_budget_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["repetitions"] = 100
        plan["max_log_bytes"] = 2 * 1024 * 1024
        with self.assertRaises(pb.Invalid):
            pb.check_plan(plan)

    def test_75_reference_comparison_keeps_reference_blocks(self):
        plan = copy.deepcopy(self.plan)
        ref = copy.deepcopy(self.lane); ref.update(name="exact_ref", role="reference", authority="exact_reference")
        plan["lanes"].append(ref)
        attempts = copy.deepcopy(self.receipt["attempts"])
        other = copy.deepcopy(attempts[0]); other["lane"] = "exact_ref"
        other["analysis"]["queries"][0]["candidate"].update(state="BLOCKED", result="UNRESOLVED", distance_cm=None, reason="REFERENCE_BLOCKED_TEST")
        attempts.append(other)
        comparisons = pb.compare_reference_lanes(plan, attempts)
        blocked = [r for r in comparisons[0]["query_comparisons"] if r["status"] == "REFERENCE_BLOCKED"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["reference_block_reason"], "REFERENCE_BLOCKED_TEST")

    def test_76_unlike_reference_bank_is_not_oracle_agreement(self):
        plan = copy.deepcopy(self.plan)
        ref = copy.deepcopy(self.lane); ref.update(name="sampled_ref", role="reference", query_class="different", authority="sampled_reference")
        plan["lanes"].append(ref)
        r = pb.compare_reference_lanes(plan, self.receipt["attempts"])
        self.assertEqual(r[0]["reason"], "UNLIKE_BANK_MODEL_OR_QUERY_CLASS")
        self.assertEqual(r[0]["query_comparisons"], [])


if __name__ == "__main__":
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    unittest.main(verbosity=2)
