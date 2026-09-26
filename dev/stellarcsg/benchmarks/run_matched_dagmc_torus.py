"""Benchmark exact-torus native and DAGMC geometry with one OpenMC binary."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


IMAGE = "parastell-openmc:0.16.0"
IMAGE_ID = "sha256:ca0c3b1fba39ce27af6ebdb79df14795041922e72521f232cdd770ff1c416191"
CONTAINER_BINARY = "/work/build/openmc-stellarcsg-dagmc-container/bin/openmc"
CONTAINER_LIBS = "/work/build/openmc-stellarcsg-dagmc-container/lib:/opt/conda/envs/parastell_damage/lib"
CASES = ("builtin_torus", "periodic_torus", "dagmc_torus_coarse", "dagmc_torus_fine")


def number(pattern: str, text: str):
    match = re.search(pattern, text, re.MULTILINE)
    return None if match is None else float(match.group(1))


def docker_command(root: Path, work: Path, debug: bool) -> list[str]:
    cross_sections = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not cross_sections:
        raise RuntimeError("OPENMC_CROSS_SECTIONS is required")
    data_dir = str(Path(cross_sections).resolve().parent)
    relative_work = work.resolve().relative_to(root.resolve()).as_posix()
    executable = f"{CONTAINER_BINARY}{' -g' if debug else ''}"
    return [
        "docker", "run", "--rm", "-e", "OMP_NUM_THREADS=1",
        "-e", "OPENMC_CROSS_SECTIONS=/data/openmc/cross_sections.xml",
        "-v", f"{root.resolve()}:/work",
        "-v", f"{data_dir}:/data/openmc:ro",
        "-w", f"/work/{relative_work}",
        "--entrypoint", "/bin/bash", IMAGE, "-lc",
        f"export LD_LIBRARY_PATH={CONTAINER_LIBS}; {executable}",
    ]


def dagmc_xml(root: Path, name: str) -> dict[str, str]:
    quality = name.rsplit("_", 1)[-1]
    h5m = f"/work/dev/stellarcsg/qualified/dagmc_exact_torus_{quality}.h5m"
    geometry = f"""<?xml version='1.0' encoding='UTF-8'?>
<geometry>
  <cell id="10000" fill="1" region="-10000" universe="2"/>
  <dagmc_universe id="1" auto_geom_ids="true" auto_mat_ids="true" filename="{h5m}"/>
  <surface id="10000" type="sphere" boundary="vacuum" coeffs="0 0 0 1000"/>
</geometry>
"""
    materials = """<?xml version='1.0' encoding='UTF-8'?>
<materials>
  <material id="1" name="Vacuum"><density value="1e-30" units="atom/b-cm"/><nuclide name="H1" ao="1"/></material>
  <material id="2" name="vacuum_comp"><density value="1e-30" units="atom/b-cm"/><nuclide name="H1" ao="1"/></material>
</materials>
"""
    settings = """<?xml version='1.0' encoding='UTF-8'?>
<settings>
  <run_mode>fixed source</run_mode><particles>200000</particles><batches>5</batches><seed>918273645</seed>
  <source type="independent" strength="1" particle="neutron"><space type="point"><parameters>500 0 0</parameters></space></source>
</settings>
"""
    return {"geometry.xml": geometry, "materials.xml": materials, "settings.xml": settings}


def prepare(root: Path, work: Path, case: str) -> None:
    work.mkdir(parents=True, exist_ok=True)
    for old in list(work.glob("*.xml")) + list(work.glob("statepoint.*.h5")):
        old.unlink()
    if case.startswith("dagmc_"):
        for filename, content in dagmc_xml(root, case).items():
            (work / filename).write_text(content)
    else:
        template = root / "dev/stellarcsg/benchmarks/models" / case / "model.xml"
        (work / "model.xml").write_text(template.read_text().replace("@ROOT@", "/work"))


def execute(root: Path, work: Path, debug: bool, allow_failure: bool = False) -> dict:
    start = time.perf_counter()
    process = subprocess.run(docker_command(root, work, debug), text=True, capture_output=True)
    elapsed = time.perf_counter() - start
    output = process.stdout + "\n" + process.stderr
    if process.returncode != 0 and not allow_failure:
        raise RuntimeError(output)
    return {
        "return_code": process.returncode,
        "wall_time_s": elapsed,
        "histories_per_s": number(r"Calculation Rate(?: \(active\))?\s*=\s*([0-9.eE+-]+)", output),
        "initialization_time_s": number(r"Total time for initialization\s*=\s*([0-9.eE+-]+)", output),
        "transport_time_s": number(r"Time in transport only\s*=\s*([0-9.eE+-]+)", output),
        "lost_particle_count": len(re.findall(r"lost particle", output, re.I)),
        "geometry_errors": len(re.findall(r"geometry error|overlapping cells detected|cell overlap error", output, re.I)),
        "overlap_checks_enabled": "CELL OVERLAP CHECK SUMMARY" in output,
        "leakage_fraction": number(r"Leakage Fraction\s*=\s*([0-9.eE+-]+)", output),
        "stdout_tail": "\n".join(output.splitlines()[-35:]),
    }


def distribution(values: list[float], stem: str) -> dict:
    return {
        f"{stem}_median": statistics.median(values),
        f"{stem}_min": min(values),
        f"{stem}_max": max(values),
        f"{stem}_iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
    }


def run_case(root: Path, case: str, repetitions: int) -> dict:
    case_root = root / "build/openmc-dagmc-matched-speed" / case
    raw = []
    for index in range(repetitions + 1):
        work = case_root / f"run_{index:02d}"
        prepare(root, work, case)
        item = execute(root, work, False)
        item.update(run=index, warmup=index == 0)
        raw.append(item)
    debug_work = case_root / "geometry_debug"
    prepare(root, debug_work, case)
    debug = execute(root, debug_work, True, allow_failure=True)
    measured = raw[1:]
    summary = {
        "case": case,
        "histories": 1000000,
        "repetitions": repetitions,
        "threads": 1,
        **distribution([x["histories_per_s"] for x in measured], "histories_per_s"),
        **distribution([x["wall_time_s"] for x in measured], "wall_time_s"),
        **distribution([x["initialization_time_s"] for x in measured], "initialization_time_s"),
        **distribution([x["transport_time_s"] for x in measured], "transport_time_s"),
        "lost_particle_count": sum(x["lost_particle_count"] for x in measured),
        "geometry_debug": debug,
        "raw": raw,
    }
    return summary


def make_plots(root: Path, cases: list[dict]) -> None:
    plot_dir = root / "dev/stellarcsg/plots/dagmc"
    plot_dir.mkdir(parents=True, exist_ok=True)
    labels = [item["case"] for item in cases]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    axes[0].bar(labels, [item["histories_per_s_median"] for item in cases],
                yerr=[0.5 * item["histories_per_s_iqr"] for item in cases], capsize=4)
    axes[0].set_ylabel("histories/s (median; half-IQR bars)")
    axes[0].tick_params(axis="x", rotation=25)
    axes[1].bar(labels, [item["initialization_time_s_median"] for item in cases])
    axes[1].set_ylabel("initialization time [s]")
    axes[1].tick_params(axis="x", rotation=25)
    figure.savefig(plot_dir / "exact_torus_speed.png", dpi=180)
    plt.close(figure)

    fidelity = json.loads((root / "dev/stellarcsg/reports/DAGMC_EXACT_TORUS_FIDELITY.json").read_text())
    mesh_error = {f"dagmc_torus_{item['name']}": item["sampled_surface_error_max_cm"]
                  for item in fidelity["meshes"]}
    errors = {"builtin_torus": 1e-16, "periodic_torus": 5.684341886080802e-14,
              **mesh_error}
    figure, axis = plt.subplots(figsize=(6.5, 4.5), constrained_layout=True)
    for item in cases:
        axis.scatter(item["histories_per_s_median"], errors[item["case"]],
                     label=item["case"])
    axis.set_yscale("log")
    axis.set_xlabel("histories/s (median)")
    axis.set_ylabel("declared/sample max geometry error [cm]")
    axis.legend(fontsize=8)
    figure.savefig(plot_dir / "exact_torus_accuracy_speed_pareto.png", dpi=180)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = root / "dev/stellarcsg/reports/DAGMC_EXACT_TORUS_SPEED.json"
    if args.plot_only:
        make_plots(root, json.loads(output.read_text())["cases"])
        return
    cases = [run_case(root, case, args.repetitions) for case in CASES]
    baseline = cases[0]["histories_per_s_median"]
    for item in cases[1:]:
        item["ratio_to_builtin"] = item["histories_per_s_median"] / baseline
    report = {
        "schema": "stellarcsg.matched-dagmc-exact-torus-speed/v1",
        "tier": "collisionless_minimal_physics_openmc_tracking",
        "openmc_branch_version": "0.15.1-dev",
        "openmc_commit": "594670eee8a0c1e26a5b44d713468f74f4204ce3",
        "binary": CONTAINER_BINARY,
        "container_image": IMAGE,
        "container_image_id": IMAGE_ID,
        "dagmc_version": "3.2.4",
        "common_seed": 918273645,
        "near_void_material": "H1 at 1e-30 atom/b-cm for DAGMC material-tag compatibility",
        "dagmc_mesh_validation": {
            "check_watertight": "PASS_ZERO_UNSEALED_SURFACES_AND_VOLUMES",
            "overlap_check_points_per_edge_3": "PASS_NO_OVERLAPS",
            "openmc_geometry_debug": "FAIL_EXPLICIT_VOLUME_VS_IMPLICIT_COMPLEMENT",
        },
        "cases": cases,
        "unavailable_fields": [
            "first-batch time", "geometry-kernel fraction", "surface-distance calls/history",
            "peak RSS and process CPU time (/usr/bin/time absent in pinned image)",
        ],
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    rows = [{k: v for k, v in case.items() if k not in ("raw", "geometry_debug")} for case in cases]
    with (root / "dev/stellarcsg/reports/DAGMC_EXACT_TORUS_SPEED.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(set().union(*rows)))
        writer.writeheader(); writer.writerows(rows)
    make_plots(root, cases)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
