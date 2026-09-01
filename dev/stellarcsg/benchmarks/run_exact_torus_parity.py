"""Run the final balanced 21-repetition exact periodic-torus parity study."""

from __future__ import annotations

import json
import random
import re
import statistics
import subprocess
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[3]
cases = {"builtin_ztorus": "builtin_torus", "periodic_exact": "periodic_torus"}
order = [name for _ in range(22) for name in cases]
random.Random(20260901).shuffle(order)
seen = {name: 0 for name in cases}
records = {name: [] for name in cases}
deps = root.parent / "openmc-stellarcsg-torus-class/build/torus-class-deps"
for name in order:
    index = seen[name]
    seen[name] += 1
    work = root / "build/exact-torus-parity-final" / name / f"run_{index:02d}"
    work.mkdir(parents=True, exist_ok=True)
    template = root / "dev/stellarcsg/benchmarks/models" / cases[name] / "model.xml"
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
    rate = float(re.search(r"Calculation Rate \(active\)\s*=\s*([0-9.eE+-]+)", output).group(1))
    records[name].append({"run": index, "warmup": index == 0, "histories_per_s": rate,
                          "lost_particles": len(re.findall("lost particle", output, re.I))})

measured = {name: np.asarray([row["histories_per_s"] for row in rows[1:]])
            for name, rows in records.items()}
rng = np.random.default_rng(20260901)
ratios = np.empty(20000)
for i in range(ratios.size):
    b = rng.choice(measured["builtin_ztorus"], measured["builtin_ztorus"].size, replace=True)
    p = rng.choice(measured["periodic_exact"], measured["periodic_exact"].size, replace=True)
    ratios[i] = np.median(p) / np.median(b)
result = {
    "schema": "stellarcsg.exact-torus-parity-final/v1",
    "hardware": "Intel Core i9-10850K", "cpu_affinity": "Docker CPU 2",
    "threads": 1, "histories_per_repetition": 1000000,
    "measured_repetitions": 21, "randomized_order": order,
    "cases": {},
    "median_ratio": float(np.median(measured["periodic_exact"]) / np.median(measured["builtin_ztorus"])),
    "bootstrap_ratio_95pct_ci": [float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))],
    "bootstrap_ratio_one_sided_95pct_lower": float(np.percentile(ratios, 5.0)),
    "noninferiority_margin": 0.03,
}
for name, values in measured.items():
    result["cases"][name] = {
        "raw_histories_per_s": values.tolist(),
        "median_histories_per_s": float(np.median(values)),
        "mean_histories_per_s": float(np.mean(values)),
        "iqr_histories_per_s": float(np.percentile(values, 75)-np.percentile(values, 25)),
        "lost_particles": sum(row["lost_particles"] for row in records[name][1:]),
        "raw": records[name],
    }
result["gates"] = {
    "hard_ratio_at_least_0_95": "PASS" if result["median_ratio"] >= 0.95 else "FAIL",
    "one_sided_95pct_excludes_slowdown_over_3pct": "PASS" if result["bootstrap_ratio_one_sided_95pct_lower"] >= 0.97 else "FAIL",
    "stretch_median_at_least_0_99": "PASS" if result["median_ratio"] >= 0.99 else "FAIL",
}
out = root / "dev/stellarcsg/benchmarks/raw/composite_blanket_interop/exact_torus_parity_21.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
