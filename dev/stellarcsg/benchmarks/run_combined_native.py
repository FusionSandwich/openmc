"""Run bounded native plasma/blanket/coil smoke and timing cases."""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import subprocess
from pathlib import Path


def number(pattern, text):
    match = re.search(pattern, text)
    return None if match is None else float(match.group(1))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    cases = ["wistell_combined_12", "wistell_combined_48"]
    order = [case for _ in range(args.repetitions + 1) for case in cases]
    random.Random(918273645).shuffle(order)
    records = {case: [] for case in cases}
    seen = {case: 0 for case in cases}
    for case in order:
        index = seen[case]
        seen[case] += 1
        work = root / "build/composite-combined" / case / f"run_{index:02d}"
        work.mkdir(parents=True, exist_ok=True)
        template = root / "dev/stellarcsg/benchmarks/models" / case / "model.xml"
        (work / "model.xml").write_text(
            template.read_text().replace("@ROOT@", "/workspace")
        )
        relative = work.relative_to(root).as_posix()
        command = [
            "docker", "run", "--rm", "--cpuset-cpus=2", "--memory=2g",
            "--memory-swap=2g", "-e", "OMP_NUM_THREADS=1", "-e",
            "OPENMC_CROSS_SECTIONS=/opt/parastell/tests/files_for_tests/cross_sections/cross_sections.xml",
            "-v", f"{root}:/workspace", "-v",
            f"{root.parent / 'openmc-stellarcsg-torus-class' / 'build/torus-class-deps'}:/workspace/build/torus-class-deps:ro",
            "-w", f"/workspace/{relative}", "parastell-openmc:0.16.0",
            "/workspace/build/composite-openmc-obb/bin/openmc",
        ]
        process = subprocess.run(command, text=True, capture_output=True)
        output = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(output)
        records[case].append({
            "run": index,
            "warmup": index == 0,
            "histories_per_s": number(r"Calculation Rate \(active\)\s*=\s*([0-9.eE+-]+)", output),
            "initialization_time_s": number(r"Total time for initialization\s*=\s*([0-9.eE+-]+)", output),
            "transport_time_s": number(r"Time in transport only\s*=\s*([0-9.eE+-]+)", output),
            "lost_particles": len(re.findall("lost particle", output, re.I)),
        })
    result = {"schema": "stellarcsg.combined-native-smoke/v1", "threads": 1,
              "histories_per_run": 10000, "cases": []}
    for case in cases:
        measured = records[case][1:]
        result["cases"].append({
            "case": case,
            "coil_count": 12 if case.endswith("12") else 48,
            "measured_repetitions": args.repetitions,
            "raw": records[case],
            "median_histories_per_s": statistics.median(
                row["histories_per_s"] for row in measured),
            "lost_particles": sum(row["lost_particles"] for row in measured),
        })
    output = root / "dev/stellarcsg/benchmarks/raw/composite_blanket_interop/combined_native_smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
