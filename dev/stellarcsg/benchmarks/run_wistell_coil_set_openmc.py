"""Run the matched one-thread WISTELL-D complete-coil-set benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import time

import h5py
import numpy as np


REPO = Path(__file__).resolve().parents[3]
ATLAS = Path(r"C:\HTS_transport\plots\stellarcsg_multiconfig_20260831")
MAGNETS = ATLAS / "wistell_d" / "magnets"
PAYLOAD = MAGNETS / "swept_coils_1cm.h5"
IMAGE = "parastell-openmc:0.16.0"
IMAGE_ID = "sha256:ca0c3b1fba39ce27af6ebdb79df14795041922e72521f232cdd770ff1c416191"
BINARY = "/work/build/openmc-stellarcsg-dagmc-container/bin/openmc"
LIBS = "/work/build/openmc-stellarcsg-dagmc-container/lib:/opt/conda/envs/parastell_damage/lib"
METHODS = ("native_csg", "dagmc_coarse", "dagmc_fine")
SEED = 918273645


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_metadata() -> dict:
    with h5py.File(PAYLOAD, "r") as handle:
        names = sorted(handle["coils"])
        first = handle["coils"][names[0]]
        centerline = np.asarray(first["centerline_coefficients"])
        normals = np.asarray(first["normal_coefficients"])
        center = (centerline[-1] + 4.0 * centerline[0] + centerline[1]) / 6.0
        tangent = 0.5 * (centerline[1] - centerline[-1])
        tangent /= np.linalg.norm(tangent)
        normal = (normals[-1] + 4.0 * normals[0] + normals[1]) / 6.0
        normal -= np.dot(normal, tangent) * tangent
        normal /= np.linalg.norm(normal)
        coefficients = np.concatenate(
            [np.asarray(handle["coils"][name]["centerline_coefficients"])
             for name in names]
        )
    return {
        "coil_count": len(names),
        "dataset_prefix": "/coils/coil_",
        "dataset_start": 1,
        "source_point_cm": (center + 2.5 * normal).tolist(),
        "source_contract": (
            "2.5 cm along the rotation-minimizing normal from coil 001 arc "
            "coordinate zero; 1.5 cm outside the standardized 1 cm tube"
        ),
        "sphere_radius_cm": float(
            np.max(np.linalg.norm(coefficients, axis=1)) + 100.0
        ),
    }


def materials_xml() -> str:
    return """<materials>
  <material id="1" name="Vacuum"><density value="1e-30" units="atom/b-cm"/><nuclide name="H1" ao="1"/></material>
  <material id="2" name="vacuum_comp"><density value="1e-30" units="atom/b-cm"/><nuclide name="H1" ao="1"/></material>
</materials>"""


def settings_xml(metadata: dict, histories: int) -> str:
    source = " ".join(f"{value:.17g}" for value in metadata["source_point_cm"])
    return f"""<settings>
  <run_mode>fixed source</run_mode><particles>{histories}</particles><batches>1</batches><seed>{SEED}</seed>
  <source type="independent" particle="neutron"><space type="point"><parameters>{source}</parameters></space></source>
</settings>"""


def native_model(metadata: dict, histories: int) -> str:
    radius = metadata["sphere_radius_cm"]
    return f"""<?xml version="1.0"?>
<model>
{materials_xml()}
<geometry>
  <surface id="1" type="swept-spline" data_file="/campaign/plots/stellarcsg_multiconfig_20260831/wistell_d/magnets/swept_coils_1cm.h5" dataset_prefix="/coils/coil_" dataset_start="1" dataset_count="48" units="cm"/>
  <surface id="2" type="sphere" coeffs="0 0 0 {radius:.17g}" boundary="vacuum"/>
  <cell id="1" material="1" region="-1"/>
  <cell id="2" material="2" region="1 -2"/>
</geometry>
{settings_xml(metadata, histories)}
</model>
"""


def dagmc_files(method: str, metadata: dict, histories: int) -> dict[str, str]:
    quality = method.rsplit("_", 1)[-1]
    mesh = (
        "/campaign/plots/stellarcsg_multiconfig_20260831/wistell_d/"
        f"magnets/coils_1cm_{quality}.h5m"
    )
    radius = metadata["sphere_radius_cm"]
    return {
        "geometry.xml": f"""<?xml version="1.0"?>
<geometry>
  <cell id="10000" fill="1" region="-10000" universe="2"/>
  <dagmc_universe id="1" auto_geom_ids="true" auto_mat_ids="true" filename="{mesh}"/>
  <surface id="10000" type="sphere" boundary="vacuum" coeffs="0 0 0 {radius:.17g}"/>
</geometry>
""",
        "materials.xml": "<?xml version=\"1.0\"?>\n" + materials_xml() + "\n",
        "settings.xml": "<?xml version=\"1.0\"?>\n" + settings_xml(metadata, histories) + "\n",
    }


def prepare(work: Path, method: str, metadata: dict, histories: int) -> None:
    work.mkdir(parents=True, exist_ok=True)
    for pattern in ("statepoint.*.h5", "summary.h5", "tallies.out"):
        for old in work.glob(pattern):
            old.unlink()
    if method == "native_csg":
        (work / "model.xml").write_text(native_model(metadata, histories))
    else:
        for name, content in dagmc_files(method, metadata, histories).items():
            (work / name).write_text(content)


def number(pattern: str, output: str) -> float | None:
    match = re.search(pattern, output, re.MULTILINE)
    return None if match is None else float(match.group(1))


def run(work: Path, debug: bool) -> dict:
    cross_sections = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not cross_sections:
        raise RuntimeError("OPENMC_CROSS_SECTIONS is required")
    relative = work.resolve().relative_to(ATLAS.resolve()).as_posix()
    command = [
        "docker", "run", "--rm", "--cpuset-cpus", "2",
        "-e", "OMP_NUM_THREADS=1",
        "-e", "OPENMC_CROSS_SECTIONS=/data/openmc/cross_sections.xml",
        "-v", f"{REPO}:/work:ro", "-v", r"C:\HTS_transport:/campaign",
        "-v", f"{Path(cross_sections).resolve().parent}:/data/openmc:ro",
        "-w", f"/campaign/plots/stellarcsg_multiconfig_20260831/{relative}",
        "--entrypoint", "/bin/bash", IMAGE, "-lc",
        f"export LD_LIBRARY_PATH={LIBS}; {BINARY}" + (" -g" if debug else ""),
    ]
    started = time.perf_counter()
    process = subprocess.run(command, text=True, capture_output=True)
    wall_time = time.perf_counter() - started
    output = process.stdout + "\n" + process.stderr
    return {
        "return_code": process.returncode,
        "wall_time_s": wall_time,
        "histories_per_s": number(
            r"Calculation Rate(?: \(active\))?\s*=\s*([0-9.eE+-]+)", output
        ),
        "initialization_time_s": number(
            r"Total time for initialization\s*=\s*([0-9.eE+-]+)", output
        ),
        "transport_time_s": number(
            r"Time in transport only\s*=\s*([0-9.eE+-]+)", output
        ),
        "leakage_fraction": number(r"Leakage Fraction\s*=\s*([0-9.eE+-]+)", output),
        "lost_particle_count": len(re.findall(r"lost particle", output, re.I)),
        "geometry_error_count": len(re.findall(
            r"geometry error|overlapping cells detected|cell overlap error",
            output, re.I)),
        "double_down_banner": "DOUBLE-DOWN interface to Embree" in output,
        "stdout_tail": "\n".join(output.splitlines()[-40:]),
    }


def statistics_record(records: list[dict]) -> dict:
    values = [item["histories_per_s"] for item in records
              if item["return_code"] == 0 and item["histories_per_s"] is not None]
    if len(values) < 2:
        return {
            "successful_repetitions": len(values),
            "raw_histories_per_s": values,
            "status": "INSUFFICIENT_SUCCESSFUL_REPETITIONS",
            "raw": records,
        }
    ordered = sorted(values)
    q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    mean = statistics.mean(ordered)
    return {
        "successful_repetitions": len(values),
        "raw_histories_per_s": values,
        "median_histories_per_s": statistics.median(ordered),
        "minimum_histories_per_s": min(ordered),
        "maximum_histories_per_s": max(ordered),
        "iqr_histories_per_s": q3 - q1,
        "coefficient_of_variation": statistics.pstdev(ordered) / mean,
        "lost_particle_count": sum(item["lost_particle_count"] for item in records),
        "geometry_error_count": sum(item["geometry_error_count"] for item in records),
        "raw": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--histories", type=int, default=100_000)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--debug-histories", type=int, default=10_000)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "dev/stellarcsg/benchmarks/raw/"
        "wistell_coil_set_openmc_20260831.json",
    )
    args = parser.parse_args()
    metadata = source_metadata()
    work_root = MAGNETS / "coil_set_benchmark_work"
    records: dict[str, list[dict]] = {method: [] for method in METHODS}

    for method in METHODS:
        work = work_root / method / "warmup"
        prepare(work, method, metadata, min(args.histories, 10_000))
        warmup = run(work, False)
        warmup["warmup"] = True
        records[method].append(warmup)

    schedule = [method for method in METHODS for _ in range(args.repetitions)]
    random.Random(SEED).shuffle(schedule)
    indices = {method: 0 for method in METHODS}
    for method in schedule:
        index = indices[method]
        indices[method] += 1
        print(f"{method} repetition {index + 1}/{args.repetitions}", flush=True)
        work = work_root / method / f"run_{index:02d}"
        prepare(work, method, metadata, args.histories)
        result = run(work, False)
        result.update(warmup=False, repetition=index)
        records[method].append(result)
        (work / "benchmark_record.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        print(json.dumps({
            "method": method,
            "repetition": index,
            "return_code": result["return_code"],
            "histories_per_s": result["histories_per_s"],
        }), flush=True)

    debug = {}
    for method in METHODS:
        work = work_root / method / "geometry_debug"
        prepare(work, method, metadata, args.debug_histories)
        debug[method] = run(work, True)

    measured = {
        method: statistics_record(
            [item for item in records[method] if not item["warmup"]]
        )
        for method in METHODS
    }
    native = measured["native_csg"].get("median_histories_per_s")
    fine = measured["dagmc_fine"].get("median_histories_per_s")
    report = {
        "schema": "stellarcsg.wistell-complete-coil-set-openmc/v1",
        "date": "2026-08-31",
        "case": "WISTELL-D complete 48-coil standardized 1 cm circular tubes",
        "source_lineage": {
            "coils_wistell_d_sha256": "7748369407d28a70f35b5c4a7c0ab860495a08fd0030002112ea933fe570159b",
            "native_payload": str(PAYLOAD),
            "native_payload_sha256": sha256(PAYLOAD),
            "dagmc_coarse_sha256": sha256(MAGNETS / "coils_1cm_coarse.h5m"),
            "dagmc_fine_sha256": sha256(MAGNETS / "coils_1cm_fine.h5m"),
        },
        "geometry": metadata,
        "hardware": "Intel Core i9-10850K; Windows 11/WSL2/Docker; CPU 2 pinned",
        "threads": 1,
        "histories_per_repetition": args.histories,
        "measured_repetitions": args.repetitions,
        "seed": SEED,
        "container_image": IMAGE,
        "container_image_id": IMAGE_ID,
        "binary": BINARY,
        "specialization": "circular swept-span local kernel; top-level BVH2 over coils",
        "production_global_reference_calls": 0,
        "results": measured,
        "ratios": {
            "native_over_fine_dagmc": (
                None if native is None or fine is None else native / fine
            ),
            "fine_dagmc_over_native": (
                None if native is None or fine is None else fine / native
            ),
        },
        "geometry_debug": debug,
        "embree_double_down": {
            "status": "NOT_RUN_UNAVAILABLE_IN_PINNED_BINARY",
            "dagmc_build": "3.2.4 nompi_nodoubledown",
            "guardrail": "Direct DAGMC results are not relabeled as Embree/Double Down.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "native_median": native,
        "fine_median": fine,
        "native_over_fine": (
            None if native is None or fine is None else native / fine
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
