"""Run matched collisionless OpenMC tracking benchmarks and retain raw timing."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def number(pattern, text):
    match = re.search(pattern, text, re.MULTILINE)
    return None if match is None else float(match.group(1))


def linux_path(path):
    path = Path(path).resolve()
    if os.name != "nt":
        return path.as_posix()
    drive = path.drive.rstrip(":").lower()
    remainder = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{remainder}"


def timed_command(binary, work):
    cross_sections = os.environ.get("OPENMC_CROSS_SECTIONS")
    data_argument = [] if not cross_sections else [
        f"OPENMC_CROSS_SECTIONS={linux_path(cross_sections)}"
    ]
    if os.name == "nt":
        return ["wsl", "-d", "Debian", "--cd", linux_path(work), "--",
                "env", "OMP_NUM_THREADS=1", *data_argument,
                linux_path(binary)]
    return ["env", "OMP_NUM_THREADS=1", *data_argument, str(binary)]


def debug_command(binary, work):
    cross_sections = os.environ.get("OPENMC_CROSS_SECTIONS")
    data_argument = [] if not cross_sections else [
        f"OPENMC_CROSS_SECTIONS={linux_path(cross_sections)}"
    ]
    if os.name == "nt":
        return ["wsl", "-d", "Debian", "--cd", linux_path(work), "--",
                "env", "OMP_NUM_THREADS=1", *data_argument,
                linux_path(binary), "-g"]
    return ["env", *data_argument, str(binary), "-g"]


def run_case(root, binary, case, repetitions, geometry_debug):
    template = root / "dev/stellarcsg/benchmarks/models" / case / "model.xml"
    work_root = root / "build/openmc-speed" / case
    work_root.mkdir(parents=True, exist_ok=True)
    raw = []
    for index in range(repetitions + 1):
        work = work_root / f"run_{index:02d}"
        work.mkdir(parents=True, exist_ok=True)
        model = template.read_text().replace("@ROOT@", linux_path(root))
        (work / "model.xml").write_text(model)
        for statepoint in work.glob("statepoint.*.h5"):
            statepoint.unlink()
        start = time.perf_counter()
        process = subprocess.run(
            timed_command(binary, work), cwd=None if os.name == "nt" else work,
            text=True, capture_output=True
        )
        elapsed = time.perf_counter() - start
        output = process.stdout + "\n" + process.stderr
        if process.returncode != 0:
            raise RuntimeError(f"{case} run {index} failed\n{output}")
        record = {
            "run": index,
            "warmup": index == 0,
            "wall_time_s": elapsed,
            "histories_per_s": number(
                r"Calculation Rate(?: \(active\))?\s*=\s*([0-9.eE+-]+)", output
            ),
            "initialization_time_s": number(
                r"Total time for initialization\s*=\s*([0-9.eE+-]+)", output
            ),
            "transport_time_s": number(
                r"Time in transport only\s*=\s*([0-9.eE+-]+)", output
            ),
            "cpu_user_s": number(r"User time \(seconds\):\s*([0-9.eE+-]+)", output),
            "cpu_system_s": number(r"System time \(seconds\):\s*([0-9.eE+-]+)", output),
            "peak_rss_kib": number(r"Maximum resident set size \(kbytes\):\s*(\d+)", output),
            "lost_particle_count": len(re.findall(r"lost particle", output, re.I)),
            "return_code": process.returncode,
            "stdout_tail": "\n".join(process.stdout.splitlines()[-30:]),
        }
        raw.append(record)
    debug = None
    if geometry_debug:
        work = work_root / "geometry_debug"
        work.mkdir(parents=True, exist_ok=True)
        (work / "model.xml").write_text(
            template.read_text().replace("@ROOT@", linux_path(root))
        )
        process = subprocess.run(
            debug_command(binary, work), cwd=None if os.name == "nt" else work,
            text=True, capture_output=True
        )
        combined = process.stdout + "\n" + process.stderr
        overlap_failures = len(re.findall(
            r"overlapping cells detected|cell overlap error", combined, re.I
        ))
        geometry_failures = len(re.findall(
            r"geometry error|lost particle", combined, re.I
        ))
        debug = {
            "return_code": process.returncode,
            "overlap_or_geometry_errors": overlap_failures + geometry_failures,
            "overlap_checks_enabled": "CELL OVERLAP CHECK SUMMARY" in combined,
            "stdout_tail": "\n".join(combined.splitlines()[-30:]),
        }
    measured = raw[1:]
    rates = [record["histories_per_s"] for record in measured]
    walls = [record["wall_time_s"] for record in measured]
    initialization = [record["initialization_time_s"] for record in measured]
    transport = [record["transport_time_s"] for record in measured]
    rss = [record["peak_rss_kib"] for record in measured
           if record["peak_rss_kib"] is not None]
    summary = {
        "case": case,
        "repetitions": repetitions,
        "histories": 1_000_000,
        "threads": 1,
        "histories_per_s_median": statistics.median(rates),
        "histories_per_s_min": min(rates),
        "histories_per_s_max": max(rates),
        "histories_per_s_iqr": float(np.percentile(rates, 75) - np.percentile(rates, 25)),
        "wall_time_s_median": statistics.median(walls),
        "wall_time_s_min": min(walls),
        "wall_time_s_max": max(walls),
        "wall_time_s_iqr": float(np.percentile(walls, 75) - np.percentile(walls, 25)),
        "initialization_time_s_median": statistics.median(initialization),
        "initialization_time_s_min": min(initialization),
        "initialization_time_s_max": max(initialization),
        "initialization_time_s_iqr": float(
            np.percentile(initialization, 75) - np.percentile(initialization, 25)
        ),
        "transport_time_s_median": statistics.median(transport),
        "transport_time_s_min": min(transport),
        "transport_time_s_max": max(transport),
        "transport_time_s_iqr": float(
            np.percentile(transport, 75) - np.percentile(transport, 25)
        ),
        "peak_rss_kib_median": None if not rss else statistics.median(rss),
        "lost_particle_count": sum(record["lost_particle_count"] for record in measured),
        "geometry_debug": debug,
        "raw": raw,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--no-debug", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    binary = root / "build/openmc-stellarcsg-enabled/bin/openmc"
    cases = ["builtin_torus", "periodic_torus", "builtin_coil", "swept_coil"]
    results = [run_case(
        root, binary, case, args.repetitions, not args.no_debug
    ) for case in cases]
    lookup = {item["case"]: item for item in results}
    lookup["periodic_torus"]["ratio_to_builtin"] = (
        lookup["periodic_torus"]["histories_per_s_median"]
        / lookup["builtin_torus"]["histories_per_s_median"]
    )
    lookup["swept_coil"]["ratio_to_builtin"] = (
        lookup["swept_coil"]["histories_per_s_median"]
        / lookup["builtin_coil"]["histories_per_s_median"]
    )
    report = {
        "schema_version": 1,
        "tier": "collisionless_minimal_physics_openmc_tracking",
        "binary": binary.as_posix(),
        "source": "isotropic point source at the centerline, default energy",
        "common_seed": 918273645,
        "cases": results,
        "unavailable_fields": [
            "first_batch_time (not separately emitted by this OpenMC build)",
            "geometry_kernel_fraction (requires profiler instrumentation)",
            "surface_distance_calls_per_history (requires counter instrumentation)",
            "peak RSS and process CPU time (/usr/bin/time is absent in the audited WSL runtime)",
            "tallies (collisionless geometry-isolation tier has no material tally)",
        ],
    }
    json_path = root / "dev/stellarcsg/reports/OPENMC_SPEED_RESULTS.json"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    rows = []
    for item in results:
        rows.append({key: value for key, value in item.items()
                     if key not in ("raw", "geometry_debug")})
    csv_path = root / "dev/stellarcsg/reports/OPENMC_SPEED_RESULTS.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set().union(*rows)))
        writer.writeheader()
        writer.writerows(rows)
    plot_dir = root / "dev/stellarcsg/plots/speed"
    plot_dir.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    axes[0].bar([item["case"] for item in results],
                [item["histories_per_s_median"] for item in results])
    axes[0].set_ylabel("histories/s")
    axes[0].tick_params(axis="x", rotation=25)
    axes[1].bar([item["case"] for item in results],
                [item["wall_time_s_median"] for item in results])
    axes[1].set_ylabel("wall time [s]")
    axes[1].tick_params(axis="x", rotation=25)
    axes[2].bar([item["case"] for item in results],
                [item["initialization_time_s_median"] for item in results])
    axes[2].set_ylabel("initialization time [s]")
    axes[2].tick_params(axis="x", rotation=25)
    figure.savefig(plot_dir / "openmc_speed_and_wall_time.png", dpi=180)
    plt.close(figure)

    accuracy = {
        "builtin_torus": 1.0e-16,
        "periodic_torus": 5.684341886080802e-14,
        "builtin_coil": 1.0e-16,
        "swept_coil": 4.725676490124897e-7,
    }
    figure, axis = plt.subplots(figsize=(6, 4), constrained_layout=True)
    for item in results:
        axis.scatter(item["histories_per_s_median"], accuracy[item["case"]],
                     label=item["case"])
    axis.set_yscale("log")
    axis.set_xlabel("histories/s (median)")
    axis.set_ylabel("declared geometry error [cm]")
    axis.legend(fontsize=8)
    figure.savefig(plot_dir / "accuracy_speed_pareto.png", dpi=180)
    plt.close(figure)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
