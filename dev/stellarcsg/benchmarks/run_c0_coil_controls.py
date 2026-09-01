"""Run paired C0 built-in, exact swept, and forced-general coil controls."""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import subprocess
from pathlib import Path

import numpy as np


def value(pattern, text):
    match = re.search(pattern, text)
    return None if match is None else float(match.group(1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=7)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    cases = {
        "C0a_builtin_ztorus": ("builtin_coil", "ordinary built-in CSG"),
        "C0b_swept_exact": ("swept_coil", "native exact-planar specialization"),
        "C0c_swept_general": ("swept_coil_forced_general", "native forced-general span solver"),
    }
    order = [name for _ in range(args.repetitions + 1) for name in cases]
    random.Random(918273645).shuffle(order)
    records = {name: [] for name in cases}
    seen = {name: 0 for name in cases}
    deps = root.parent / "openmc-stellarcsg-torus-class/build/torus-class-deps"
    for name in order:
        index = seen[name]
        seen[name] += 1
        template_name, _ = cases[name]
        work = root / "build/c0-coil-controls" / name / f"run_{index:02d}"
        work.mkdir(parents=True, exist_ok=True)
        template = root / "dev/stellarcsg/benchmarks/models" / template_name / "model.xml"
        (work / "model.xml").write_text(template.read_text().replace("@ROOT@", "/workspace"))
        command = ["docker", "run", "--rm", "--cpuset-cpus=2", "--memory=2g",
                   "--memory-swap=2g", "-e", "OMP_NUM_THREADS=1", "-e",
                   "OPENMC_CROSS_SECTIONS=/opt/parastell/tests/files_for_tests/cross_sections/cross_sections.xml",
                   "-v", f"{root}:/workspace", "-v", f"{deps}:/workspace/build/torus-class-deps:ro",
                   "-w", f"/workspace/{work.relative_to(root).as_posix()}",
                   "parastell-openmc:0.16.0", "/workspace/build/composite-openmc-obb/bin/openmc"]
        process = subprocess.run(command, text=True, capture_output=True)
        output = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(output)
        records[name].append({
            "run": index, "warmup": index == 0,
            "histories_per_s": value(r"Calculation Rate \(active\)\s*=\s*([0-9.eE+-]+)", output),
            "initialization_time_s": value(r"Total time for initialization\s*=\s*([0-9.eE+-]+)", output),
            "transport_time_s": value(r"Time in transport only\s*=\s*([0-9.eE+-]+)", output),
            "lost_particles": len(re.findall("lost particle", output, re.I)),
        })
    summaries = []
    for name, (_, method) in cases.items():
        measured = records[name][1:]
        rates = [row["histories_per_s"] for row in measured]
        summaries.append({
            "case": name, "method": method,
            "specialization": "exact planar torus" if name.endswith("exact") else
                              ("disabled" if name.endswith("general") else "built-in ZTorus"),
            "raw_histories_per_s": rates,
            "median_histories_per_s": statistics.median(rates),
            "iqr_histories_per_s": float(np.percentile(rates, 75) - np.percentile(rates, 25)),
            "lost_particles": sum(row["lost_particles"] for row in measured),
            "raw": records[name],
        })
    baseline = summaries[0]["median_histories_per_s"]
    for row in summaries:
        row["ratio_to_builtin"] = row["median_histories_per_s"] / baseline
    result = {"schema": "stellarcsg.c0-coil-controls/v1", "hardware": "Intel Core i9-10850K",
              "threads": 1, "cpu_affinity": "Docker CPU 2", "histories": 1000000,
              "measured_repetitions": args.repetitions, "seed": 918273645,
              "randomized_order": order, "cases": summaries,
              "root_oracle": "permanent adapter test compares exact swept roots directly with openmc::torus_distance",
              "production_global_oracle_calls": 0}
    out = root / "dev/stellarcsg/benchmarks/raw/composite_blanket_interop/c0_coil_controls.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
