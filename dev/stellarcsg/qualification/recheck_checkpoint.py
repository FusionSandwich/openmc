#!/usr/bin/env python3
"""Re-read checkpoint evidence and run bounded synthetic parser counterexamples.

No build, acquisition, native transport, or physical-source admission occurs.
This is a checkpoint review, not a solver qualification test.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest
from tempfile import TemporaryDirectory


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    root = Path(__file__).resolve().parents[3]
    base = root / "dev/stellarcsg"
    reports = base / "reports/local-cont-20260925"
    checks = []

    def check(label, path, expected):
        actual = sha(path) if path.is_file() else None
        checks.append({"label": label, "path": str(path.relative_to(root)),
                       "expected_sha256": expected, "actual_sha256": actual,
                       "match": actual == expected})

    horner = load(reports / "compiled-horner-enclosure-03.json")
    for label, relative in {
        "auditor": "qualification/audit_compiled_horner_enclosure.py",
        "boxes": "reports/local-cont-20260925/compiled-span-boxes-01.jsonl",
        "construction_receipt": "reports/local-cont-20260925/compiled-box-construction-01.receipt.json",
        "production_source": "src/compiled_swept_surface.cpp",
    }.items():
        check("horner/" + label, base / relative, horner["hashes"][label])

    for name in ("p00-magnet-material-bank-02", "p00-magnet-union-bank-01"):
        receipt = load(reports / name / "receipt.json")
        for filename in ("geometry.xml", "materials.xml", "settings.xml", "source.h5",
                         "tracks.h5", "statepoint.1.h5", "summary.h5"):
            check(name + "/" + filename, reports / name / filename,
                  receipt["hashes"][filename])
        check(name + "/facet_payload", reports / "p00-periodic-facet-candidate-02.h5",
              receipt["hashes"]["facet_payload"])
    equivalent = load(reports / "p00-magnet-union-equivalence-02.json")
    for label, relative in {
        "auditor": "qualification/audit_p00_magnet_union_equivalence.py",
        "priority_receipt": "reports/local-cont-20260925/p00-magnet-material-bank-02/receipt.json",
        "union_receipt": "reports/local-cont-20260925/p00-magnet-union-bank-01/receipt.json",
        "priority_tracks": "reports/local-cont-20260925/p00-magnet-material-bank-02/tracks.h5",
        "union_tracks": "reports/local-cont-20260925/p00-magnet-union-bank-01/tracks.h5",
    }.items():
        check("union_equivalence/" + label, base / relative, equivalent["hashes"][label])

    candidate_path = reports / "same-span-prefix-bank-01/candidate-0.jsonl"
    exact_path = reports / "strict-old-01/exact-reference-0.jsonl"
    candidate_rows = [json.loads(x) for x in candidate_path.read_text().splitlines()]
    exact_rows = [json.loads(x) for x in exact_path.read_text().splitlines()]
    candidate = {x["id"]: x for x in candidate_rows if x.get("kind") == "query"}
    exact = {x["id"]: x for x in exact_rows if x.get("kind") == "query"}
    assert len(candidate) == len(exact) == 160 and set(candidate) == set(exact)
    provenance_mismatches = []
    resolved_mismatches = []
    for key, row in candidate.items():
        oracle = exact[key]
        if any(row.get(k) != oracle.get(k) for k in ("coefficient_hash", "source_sha256")):
            provenance_mismatches.append(key)
        if row.get("candidate_disposition") != "unresolved":
            found = row.get("candidate_found")
            if found != oracle.get("candidate_found"):
                resolved_mismatches.append(key)
            elif found:
                a, b = row.get("candidate_distance"), oracle.get("candidate_distance")
                if (type(a) not in (int, float) or type(b) not in (int, float)
                        or not math.isfinite(a) or not math.isfinite(b) or abs(a-b) > 2e-8):
                    resolved_mismatches.append(key)

    spec = importlib.util.spec_from_file_location(
        "source_fixture", base / "tests/test_plasma_source_handoff.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    names = unittest.TestLoader().getTestCaseNames(fixture.PlasmaSourceHandoffTests)
    # The constructor test imports OpenMC and belongs to the separately run
    # existing OpenMC environment, not this stdlib-only review.
    names.remove("test_synthetic_constructor_contract")
    suite_output = io.StringIO()
    suite = unittest.TextTestRunner(stream=suite_output).run(unittest.TestSuite(
        fixture.PlasmaSourceHandoffTests(name) for name in names))
    with TemporaryDirectory(prefix="stellarcsg-checkpoint-") as temporary:
        temporary = Path(temporary)
        fake_candidate = temporary / "nan-candidate.jsonl"
        copied = [dict(row) for row in exact_rows]
        hit = next(row for row in copied if row.get("kind") == "query" and row.get("candidate_found"))
        hit["candidate_distance"] = float("nan")
        fake_candidate.write_text("\n".join(json.dumps(row) for row in copied) + "\n")
        comparison = subprocess.run([
            sys.executable, "-B", str(base / "qualification/compare_frozen_oracle.py"),
            "--candidate", str(fake_candidate), "--exact", str(exact_path),
            "--output", str(temporary / "comparison.json")],
            cwd=root, capture_output=True, text=True, timeout=30)

        source_dir = temporary / "source"
        source_dir.mkdir()
        handoff_path = fixture.synthetic_bundle(source_dir)
        handoff = load(handoff_path)
        sampling_path = source_dir / handoff["files"]["sampling_result"]["name"]
        sampling = load(sampling_path)
        bindings = sampling["input_sha256"]
        bindings["source"], bindings["mesh"] = bindings["mesh"], bindings["source"]
        sampling_path.write_text(json.dumps(sampling, allow_nan=False) + "\n")
        handoff["files"]["sampling_result"]["sha256"] = sha(sampling_path)
        handoff_path.write_text(json.dumps(handoff, allow_nan=False) + "\n")
        accepted = False
        error = None
        try:
            fixture.load_bounded_plasma_source(
                handoff_path, expected_wall_sha256=handoff["files"]["wall"]["sha256"])
            accepted = True
        except ValueError as exc:
            error = str(exc)

    report = {
        "schema": "stellarcsg.checkpoint-review/v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "reviewer_script_sha256": sha(__file__),
        "artifact_hash_checks": checks,
        "artifact_hashes_match": all(x["match"] for x in checks),
        "saved_latest_strict_bank": {
            "candidate_sha256": sha(candidate_path), "exact_sha256": sha(exact_path),
            "dispositions": dict(Counter(x.get("candidate_disposition") for x in candidate.values())),
            "known_wrong_root_ids_now_unresolved": all(candidate[k].get("candidate_disposition") == "unresolved"
                                                       for k in ("a03", "a06", "a08", "a15")),
            "provenance_mismatches": provenance_mismatches,
            "resolved_mismatches": resolved_mismatches,
            "nonfinite_found_distances": [x["id"] for x in candidate.values()
                if x.get("candidate_found") and (type(x.get("candidate_distance")) not in (int, float)
                                                or not math.isfinite(x["candidate_distance"]))],
            "qualification": "HISTORICAL_REPLAY_NOT_FRESH_HEAD_EXECUTION",
        },
        "synthetic_source_suite": {"exit_code": 0 if suite.wasSuccessful() else 1,
                                   "tests_run": suite.testsRun, "output": suite_output.getvalue(),
                                   "constructor_test": "NOT_RUN_BY_STDLIB_REVIEW_REQUIRES_OPENMC"},
        "synthetic_negative_controls": {
            "nan_distance": {"query_id": hit["id"], "comparison_exit_code": comparison.returncode,
                             "stdout": comparison.stdout, "stderr": comparison.stderr,
                             "false_pass_reproduced": comparison.returncode == 0},
            "swapped_sampling_input_hashes": {"accepted": accepted, "error": error,
                                              "false_pass_reproduced": accepted},
        },
        "claim_boundary": "Stored artifact identities and bounded synthetic parser controls only. No rebuild, fresh native replay, mathematical proof rerun, physical source admission or new transport.",
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"artifact_hashes_match": report["artifact_hashes_match"],
                      "hash_checks": len(checks), "strict_bank": report["saved_latest_strict_bank"],
                      "source_suite_exit": report["synthetic_source_suite"]["exit_code"],
                      "negative_controls": report["synthetic_negative_controls"]}, allow_nan=False))
    return 0 if report["artifact_hashes_match"] and suite.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
