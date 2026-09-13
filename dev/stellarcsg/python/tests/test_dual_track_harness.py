from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


HARNESS = Path(__file__).parents[2] / "benchmarks" / "dual_track_harness.py"
SPEC = importlib.util.spec_from_file_location("dual_track_harness", HARNESS)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_summary_retains_required_statistics():
    result = MODULE.summary([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result["median"] == 3.0
    assert result["mean"] == 3.0
    assert result["iqr"] == 2.0
    assert result["coefficient_of_variation"] > 0.0


def test_balanced_schedule_rotates_each_method_through_first_position():
    result = MODULE.schedule(["a", "b", "c"], 9, "balanced", 17)
    assert len(result) == 9
    assert all(sorted(row) == ["a", "b", "c"] for row in result)
    first_counts = {name: sum(row[0] == name for row in result) for name in "abc"}
    assert max(first_counts.values()) - min(first_counts.values()) <= 1


def test_schedule_rejects_too_few_repetitions():
    with pytest.raises(ValueError, match="seven"):
        MODULE.schedule(["a", "b"], 6, "balanced", 1)


def test_paired_bootstrap_identity_is_exact():
    interval = MODULE.paired_bootstrap_ratio(
        [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0],
        [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0],
        seed=9,
        samples=1000,
    )
    assert interval == [1.0, 1.0]


@pytest.fixture
def campaign(tmp_path):
    def artifact(name, text):
        path = tmp_path / name
        path.write_text(text)
        return {"path": str(path), "sha256": MODULE.sha256_file(path)}

    script = artifact("command.py", "print('unused')")
    command = [sys.executable, script["path"]]
    return {
        "case_id": "harness_test_only",
        "sentinel_method": "native",
        "protocol": {"warmups": 1, "measured_repetitions": 7,
                     "thread_count": 1, "order_policy": "balanced", "seed": 17},
        "common_artifacts": {name: artifact(name, name)
                             for name in ("source_geometry", "source_bank", "settings")},
        "methods": [{
            "id": name, "command": command,
            "artifacts": {"binary": {"path": sys.executable,
                                     "sha256": MODULE.sha256_file(Path(sys.executable))},
                          "script": script,
                          "compiled_geometry": artifact(name + "geometry", name)},
            "metadata": {"build_commit": "a" * 40, "harness_commit": "b" * 40,
                         "hardware": "test", "cpu_affinity": "0", "thread_count": 1,
                         "libraries": [], "surface_method": method},
        } for name, method in (("native", "builtin_ztorus"), ("candidate", "bezier_atlas_v2"))],
    }


def successful_attempt(method):
    return {"valid": True, "invalid_reasons": [],
            "payload": {"histories_per_s": 2.0, "active_transport_seconds": 1.0,
                        "total_wall_seconds": 2.0}}


def test_distinct_method_artifacts_are_allowed(campaign):
    MODULE.validate_campaign(campaign)


def test_binary_artifact_must_bind_executed_program(campaign):
    method = campaign["methods"][0]
    method["artifacts"]["binary"] = method["artifacts"]["compiled_geometry"]
    with pytest.raises(ValueError, match="does not bind command executable"):
        MODULE.validate_campaign(campaign)


def test_dagmc_requires_identical_h5m(campaign):
    ordinary = dict(campaign["methods"][1])
    ordinary.update(id="ordinary", metadata={**ordinary["metadata"], "surface_method": "ordinary_dagmc"})
    ordinary["artifacts"] = {**ordinary["artifacts"], "h5m": ordinary["artifacts"]["compiled_geometry"]}
    doubledown = {**ordinary, "id": "dd", "metadata": {**ordinary["metadata"], "surface_method": "double_down_embree"},
                  "artifacts": {**ordinary["artifacts"], "h5m": campaign["methods"][0]["artifacts"]["compiled_geometry"]}}
    campaign["methods"].extend([ordinary, doubledown])
    with pytest.raises(ValueError, match="identical H5M"):
        MODULE.validate_campaign(campaign)


def test_hash_drift_is_retained_and_blocks_campaign(campaign, tmp_path, monkeypatch):
    calls = []

    def mutate(method):
        calls.append(method["id"])
        Path(campaign["common_artifacts"]["settings"]["path"]).write_text("changed")
        return successful_attempt(method)

    monkeypatch.setattr(MODULE, "invoke", mutate)
    journal = tmp_path / "attempts.jsonl"
    result = MODULE.run_campaign(campaign, journal_path=journal)
    records = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len(calls) == 1
    assert result["gate_status"] == "BLOCKED"
    assert len(result["attempts"]) == 16
    assert len([row for row in records if row["event"] == "finished"]) == 16
    assert "post-attempt drift" in result["attempts"][0]["invalid_reasons"][0]
    assert result["aggregates"]["candidate"]["valid_pair_count"] == 0


def test_failed_attempt_keeps_all_records_and_complete_pairs(campaign, tmp_path, monkeypatch):
    calls = []

    def run(method):
        calls.append(method["id"])
        if len(calls) == 3:
            raise OSError("retained failure")
        return successful_attempt(method)

    monkeypatch.setattr(MODULE, "invoke", run)
    result = MODULE.run_campaign(campaign, journal_path=tmp_path / "attempts.jsonl")
    assert len(result["attempts"]) == 16
    assert result["gate_status"] == "BLOCKED"
    assert result["aggregates"]["candidate"]["valid_pair_count"] == 6
    assert result["aggregates"]["candidate"]["bootstrap_ratio_interval_95"] is None


def test_journal_refuses_overwrite(campaign, tmp_path, monkeypatch):
    journal = tmp_path / "attempts.jsonl"
    journal.write_text("original\n")
    monkeypatch.setattr(MODULE, "invoke", lambda method: pytest.fail("must not execute"))
    with pytest.raises(FileExistsError):
        MODULE.run_campaign(campaign, journal_path=journal)
    assert journal.read_text() == "original\n"


@pytest.mark.parametrize("stdout", ["not json", "[]", '{"histories_per_s":NaN}',
                                  json.dumps({"histories_per_s": 10**400}),
                                  '{"histories_per_s":1,"active_transport_seconds":2,"total_wall_seconds":1}'])
def test_invalid_command_output_is_retained(stdout, monkeypatch):
    import subprocess
    monkeypatch.setattr(MODULE.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 0, stdout, "diagnostic"))
    result = MODULE.invoke({"id": "test", "command": [sys.executable]})
    assert not result["valid"]
    assert result["stdout"] == stdout
    assert result["stderr"] == "diagnostic"


def test_nonzero_command_exit_is_retained(monkeypatch):
    import subprocess
    stdout = json.dumps(successful_attempt(None)["payload"])
    monkeypatch.setattr(MODULE.subprocess, "run", lambda *args, **kwargs:
                        subprocess.CompletedProcess(args[0], 4, stdout, "failure"))
    result = MODULE.invoke({"id": "test", "command": [sys.executable]})
    assert not result["valid"]
    assert result["return_code"] == 4
    assert result["stdout"] == stdout


def test_successful_timing_is_not_geometry_qualification(campaign, tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "invoke", successful_attempt)
    result = MODULE.run_campaign(campaign, journal_path=tmp_path / "attempts.jsonl")
    assert result["gate_status"] == "NOT_RUN"
    assert result["aggregates"]["candidate"]["valid_pair_count"] == 7
    assert result["aggregates"]["candidate"]["ratio_denominator"] == "native"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0.0, -1.0])
def test_nonfinite_or_nonpositive_statistics_rejected(value):
    with pytest.raises(ValueError, match="finite and positive"):
        MODULE.summary([value])
    with pytest.raises(ValueError, match="finite and positive"):
        MODULE.paired_bootstrap_ratio([1.0], [value], seed=1)
