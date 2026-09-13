"""Audit and plot retained plasma replay evidence; never execute a benchmark."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path, help="Output basename, without suffix")
    args = parser.parse_args()
    data = json.loads(args.campaign.read_text())
    manifest, attempts = data["manifest"], data["attempts"]
    harness_path = Path(__file__).with_name("dual_track_harness.py")
    spec = importlib.util.spec_from_file_location("neutral_harness", harness_path)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    assert data["block_valid"] and len(attempts) == 72
    journal_path = args.campaign.with_name("attempts.jsonl")
    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    assert Counter(row["event"] for row in journal) == {"campaign": 1, "started": 72, "finished": 72}
    assert journal[0]["manifest"] == manifest
    finishes = [row for row in journal if row["event"] == "finished"]
    assert [{k: v for k, v in row.items() if k != "event"} for row in finishes] == attempts
    starts = [row for row in journal if row["event"] == "started"]
    methods = manifest["methods"]
    assert len(methods) == 9
    shared = manifest["shared_artifacts"]
    frozen = {}
    for case in ("helical", "wistell"):
        item = next(x for x in shared if x["path"].endswith(f"-{case}-correctness-01.jsonl"))
        assert sha(item["path"]) == item["sha256"]
        frozen[case] = [json.loads(line) for line in Path(item["path"]).read_text().splitlines()
                        if json.loads(line)["kind"] == "ray"]
    model_record = next(x for x in shared if x["path"].endswith("/model.xml"))
    expected_counts = Counter((m, phase) for m in methods for phase in ["warmup"] + ["measured"]*7)
    assert Counter((r["method_id"], r["phase"]) for r in attempts) == expected_counts
    sentinel_histories = 0
    checked_outputs = 0
    for start, row in zip(starts, attempts):
        method = methods[row["method_id"]]
        assert row["valid"] and not row["invalid_reasons"] and row["return_code"] == 0
        assert start["command"] == method["command"]
        assert method["command"][0] == method["artifacts"][0]["resolved_path"]
        assert start["expected_hashes"] == shared + method["artifacts"] + method["libraries"]
        for record in row["output_hashes"]:
            assert sha(record["path"]) == record["sha256"]
            checked_outputs += 1
        stdout = Path(row["stdout_file"]).read_text()
        stderr = Path(row["stderr_file"]).read_text()
        assert not stderr.strip()
        if row["kernel_summary"] is not None:
            payloads = [json.loads(line) for line in stdout.splitlines()]
            assert [r for r in payloads if r["kind"] == "ray"] == frozen[method["case"]]
            assert payloads[-1] == row["kernel_summary"]
        else:
            directory = Path(row["stdout_file"]).parent
            assert sha(directory / "model.xml") == model_record["sha256"]
            model = ET.parse(directory / "model.xml").getroot()
            with h5py.File(directory / "statepoint.10.h5") as statepoint:
                batches = int(statepoint["n_batches"][()])
                particles = int(statepoint["n_particles"][()])
                assert (batches, particles) == (10, 1000)
                assert batches == int(model.findtext("settings/batches"))
                assert particles == int(model.findtext("settings/particles"))
                assert int(statepoint["n_realizations"][()]) == batches
            assert "Simulating batch 10" in stdout
            assert "lost particle" not in stdout.lower()
            sentinel_histories += batches*particles
    assert sentinel_histories == 80000 and checked_outputs == 144

    measured = [row for row in attempts if row["phase"] == "measured"]
    groups = {key: [row for row in measured if row["method_id"] == key] for key in methods}
    timings = {key: [r["kernel_summary"]["ns_per_query"] for r in rows]
               for key, rows in groups.items() if rows[0]["kernel_summary"] is not None}
    overhead = []
    for case in ("helical", "wistell"):
        for version in ("baseline", "candidate"):
            on, off = timings[f"{case}-{version}-on"], timings[f"{case}-{version}-off"]
            ratio = statistics.median(on)/statistics.median(off)
            low, high = harness.paired_bootstrap_ratio(on, off, seed=713)
            overhead.append(dict(case=case, version=version, ratio=ratio,
                interval_95=[low, high], definition="counter ON ns/query divided by OFF; >1 is overhead"))
    tails = {}
    for key in timings:
        tails[key] = {stat: [r["kernel_summary"][f"separate_diagnostic_{stat}_ns"] for r in groups[key]]
                      for stat in ("min", "p95", "max")}
    summary = dict(
        schema="stellarcsg.plasma-ablation-plot/v1", qualification="NOT_RUN",
        source=dict(path=str(args.campaign), sha256=sha(args.campaign),
                    journal_sha256=sha(journal_path), generator_sha256=sha(__file__)),
        audit=dict(attempts=72, warmup_attempts=9, measured_attempts=63,
                   durable_started_records=72, durable_finished_records=72,
                   output_hashes_verified=144, sentinel_histories_including_warmup=80000,
                   sentinel_measured_histories=70000, frozen_kernel_records_unchanged=True),
        methods={key: dict(command=value["command"], artifacts=value["artifacts"],
                          declared_source_commit=value.get("declared_source_commit"),
                          linked_library_count=len(value["libraries"]),
                          linked_library_manifest_sha256=hashlib.sha256(json.dumps(value["libraries"],
                              sort_keys=True).encode()).hexdigest()) for key, value in methods.items()},
        comparisons=data["comparisons"], counter_overhead=overhead,
        measured_ns_per_query=timings, separate_diagnostic_tails_ns=tails,
        sentinel=data["sentinel_histories_per_s"],
        interpretation={"helical_off": "3.4% faster in this replay; 95% paired bootstrap interval above 1",
                        "wistell_off": "inconclusive; five inherited unresolved oracle rays remain BLOCKED"},
        limitations=["Seven repetitions: continuation ablation, not decisive or transport qualification.",
                     "Counter-overhead ratios include timing noise; values below 1 do not establish negative instrumentation cost.",
                     "Tails are single 256-query diagnostic passes, outside main timed loops; no tail confidence claim.",
                     "Native sentinel CV is 9.9%; first measured sentinel is slower. Retained without selective exclusion.",
                     "Nine methods rotated over seven measured rounds: partial position balance, not a full nine-round cycle.",
                     "Uncontrolled desktop activity and cache effects remain possible.",
                     "Hashes bind executables and runtime artifacts; source SHA association relies on coordinator build receipts.",
                     "No native-torus or Embree performance ratio is inferred."])

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
    colors = {"helical": "#176b92", "wistell": "#a55624"}
    ax = axes[0, 0]
    labels = []
    for i, (case, version) in enumerate((c, v) for c in ("helical", "wistell") for v in ("baseline", "candidate")):
        values = [v/1000 for v in timings[f"{case}-{version}-off"]]
        ax.scatter([i + (j-3)*.025 for j in range(7)], values, color=colors[case], alpha=.6, s=25)
        ax.plot([i-.2, i+.2], [statistics.median(values)]*2, color="black", linewidth=2)
        labels.append(f"{case.title()}\n{version}")
    ax.set(xticks=range(4), xticklabels=labels, ylabel="Distance query time (µs)", title="Counters OFF: all seven measured repetitions")
    ax = axes[0, 1]
    comparisons = sorted(data["comparisons"], key=lambda row: (row["case"], row["counters"]))
    for i, row in enumerate(comparisons):
        ratio = row["speed_ratio"]
        low, high = row["paired_bootstrap_interval_95"]
        ax.errorbar(ratio, i, xerr=[[ratio-low], [high-ratio]], fmt="o", capsize=4, color=colors[row["case"]])
        ax.text(high+.005, i, f"{ratio:.3f}", va="center", fontsize=9)
    ax.axvline(1, color="gray", linestyle="--")
    ax.set(yticks=range(4), yticklabels=[f"{r['case'].title()} {r['counters'].upper()}" for r in comparisons],
           xlabel="Baseline / candidate ns per query  (>1 faster)", title="Speed ratios with paired bootstrap 95% intervals", xlim=(.93, 1.23))
    ax.invert_yaxis()
    ax = axes[1, 0]
    for i, row in enumerate(overhead):
        low, high = row["interval_95"]
        ax.errorbar(row["ratio"], i, xerr=[[row["ratio"]-low], [high-row["ratio"]]],
                    fmt="o", color=colors[row["case"]], capsize=4)
    ax.axvline(1, color="gray", linestyle="--")
    ax.set(yticks=range(4), yticklabels=[f"{r['case'].title()} {r['version']}" for r in overhead],
           xlabel="ON / OFF ns per query  (>1 overhead)", title="Counter cost: noisy paired estimates (95% intervals)")
    ax.invert_yaxis()
    ax = axes[1, 1]
    keys = list(timings)
    for stat, marker in (("min", "v"), ("p95", "o"), ("max", "^")):
        ax.plot(range(len(keys)), [statistics.median(tails[key][stat])/1000 for key in keys],
                marker=marker, label=stat, linewidth=1)
    ax.set(xticks=range(len(keys)), xticklabels=[key.replace("helical", "H").replace("wistell", "W").replace("baseline", "base").replace("candidate", "new") for key in keys],
           ylabel="Median of seven diagnostic pass statistics (µs)", title="Single-pass query tails; no tail qualification")
    ax.tick_params(axis="x", labelrotation=40)
    ax.set_yscale("log")
    ax.legend(frameon=False, ncol=3)
    fig.suptitle("Periodic plasma ablation: modest helical gain; WISTELL-D inconclusive", fontsize=15)
    fig.text(.06, .035, "256 fixed rays × 128 banks; 1 warmup + 7 measured rounds; CPU 0. WISTELL-D: 5 BLOCKED rays.\n"
             "Native ZTorus sentinel: 185,377 histories/s median, 9.9% CV; 80,000 histories including warmup.\n"
             "Kernel diagnostics only. Near-torus, Embree advantage, and transport qualification: NOT_RUN.", fontsize=10)
    fig.tight_layout(rect=(0, .12, 1, .96), h_pad=2.2, w_pad=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output.with_suffix(".png"), dpi=150)
    args.output.with_suffix(".json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(json.dumps(summary["audit"]))


if __name__ == "__main__":
    main()
