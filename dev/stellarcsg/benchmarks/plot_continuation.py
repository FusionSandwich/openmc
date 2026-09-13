"""Plot retained continuation measurements; never generates substitute data."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def counter_observations(phase):
    """Describe measured counter coverage without converting absence to zero."""
    counters = phase["counters"]
    if counters is None:
        return dict(counters_per_call=None, counter_coverage={
            "state": "unavailable", "reason": "performance counters disabled"})
    available = {"distance_calls", "evaluate_calls", "normal_calls"}
    if phase["operation"] == "evaluate":
        available.update({"cache_hits", "cache_misses"})
    values = {}
    for name, value in counters.items():
        if isinstance(value, int):
            observed = phase["operation"] == "distance" or name in available
            values[name] = value / phase["calls"] if observed else None
    return dict(counters_per_call=values, counter_coverage={
        "scope": "existing instrumented events, not complete nested search accounting",
        "available": sorted(name for name, value in values.items() if value is not None),
        "unavailable": sorted(name for name, value in values.items() if value is None),
        "unavailable_reason": (
            "evaluate/normal local-coordinate search and solve work is not instrumented; "
            "raw zero counters do not measure absence of that work"),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel-sha", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = {}

    def read(relative):
        data = (args.raw / relative).read_bytes()
        inputs[relative] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    before = read("baseline-polynomial-05.json")
    after = read("a-repair-polynomial-01.json")
    profiles = [read(f"profile-runs-02/{i:02d}.json") for i in range(1, 8)]
    campaign = read("profile-runs-02/campaign.json")
    native = read("b-native-smoke/run-01/receipt.json")
    metrics = dict(kernel_sha=args.kernel_sha, qualification="NOT_RUN",
                   profile_instrumented=True, measured_repetitions=7,
                   before_counts=before["counts"], after_counts=after["counts"],
                   peak_child_rss_kib=campaign["peak_child_rss_kib"],
                   native_initialization=native, phases=[])
    rng = np.random.default_rng(713)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ci, label in enumerate(["Non-planar circular coil", "Helical plasma"]):
        axis = axes[ci]
        case = profiles[0]["cases"][ci]
        for pi, phase in enumerate(case["phases"]):
            values = np.array([p["cases"][ci]["phases"][pi]["ns_per_query"]
                               for p in profiles])
            boot = np.median(rng.choice(values, (10000, 7)), axis=1)
            interval = np.quantile(boot, [0.025, 0.975]).tolist()
            metrics["phases"].append(dict(
                method=case["method"], operation=phase["operation"],
                median_ns=float(np.median(values)),
                min_ns=float(min(values)), max_ns=float(max(values)),
                iqr_ns=float(np.quantile(values, .75)-np.quantile(values, .25)),
                bootstrap_median_interval_95_ns=interval,
                samples_ns=values.tolist(),
                bound_check_state=phase.get("bound_check_state", "NOT_RUN"),
                calls_per_repetition=phase["calls"],
                **counter_observations(phase)))
            axis.scatter(pi + np.linspace(-.10, .10, 7), values/1000,
                         s=27, color="#1967a3", alpha=.7)
            axis.plot([pi-.2, pi+.2], [np.median(values)/1000]*2,
                      color="#142938", lw=2)
        axis.set_title(label)
        axis.set_xticks(range(3), [p["operation"] for p in case["phases"]])
        axis.set_ylabel("Instrumented µs / query (log scale)")
        axis.set_yscale("log")
        axis.grid(axis="y", alpha=.2)
    fig.suptitle("Measured kernel profiles — separate synthetic workloads")
    fig.text(.5, .035, "7 retained runs after warm-up · 51,200 calls / phase / run · CPU 0 · "
             "no transport or speed qualification", ha="center", fontsize=9)
    fig.text(.5, .005, f"Kernel {args.kernel_sha[:12]} · Windows i9-10850K / OpenMC-Dev-D · "
             "desktop interference uncontrolled", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .10, 1, .94))
    fig.savefig(args.output / "query_profile.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    bottom = np.zeros(2)
    for state, color in [("PASS", "#357d59"), ("FAIL", "#bb4b43"), ("BLOCKED", "#c38b32")]:
        values = np.array([before["counts"][state], after["counts"][state]])
        axes[0].bar([0, 1], values, bottom=bottom, color=color, label=state)
        for x, value, base in zip([0, 1], values, bottom):
            if value:
                axes[0].text(x, base+value/2, str(value), color="white", ha="center", va="center")
        bottom += values
    axes[0].set_xticks([0, 1], ["Baseline", "Scoped repair"])
    axes[0].set_ylabel("Fixed rays")
    axes[0].set_title("Sampled independent polynomial oracle")
    axes[0].legend(loc="upper center", bbox_to_anchor=(.5, -.10), ncol=3, frameon=False)
    for shape, offset, label in [(0, -.12, "Planar"), (1, .12, "Non-planar")]:
        values = [next(r["distance"] for r in report["results"]
                       if r["shape"] == shape and r["index"] == 8)
                  for report in [before, after]]
        axes[1].bar(np.array([0, 1])+offset, values, width=.23, label=label)
    axes[1].axhline(.002, color="black", linestyle="--", linewidth=1,
                    label="Known surface hit: 0.002 cm")
    axes[1].set_yscale("log")
    axes[1].set_xticks([0, 1], ["Baseline", "Scoped repair"])
    axes[1].set_ylabel("Returned distance (cm)")
    axes[1].set_title("Two independently proven missed entries")
    axes[1].legend(fontsize=8, loc="upper right")
    fig.suptitle("Retained before / after correctness evidence")
    fig.text(.5, .035, "87 repaired oracle failures belong to an unqualified stress shape. "
             "23 cases remain BLOCKED; completeness is not certified.", ha="center", fontsize=9)
    fig.text(.5, .005, f"Baseline capture SHA-256 {before['input_sha256'][:16]}… · "
             f"repaired {after['input_sha256'][:16]}…", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .10, 1, .94))
    fig.savefig(args.output / "root_repair.png", dpi=160)
    plt.close(fig)
    metrics["raw_sha256"] = inputs
    (args.output / "measurements.json").write_text(json.dumps(metrics, indent=2)+"\n")
    print(json.dumps(metrics["phases"], indent=2))


if __name__ == "__main__":
    main()
