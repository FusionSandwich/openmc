#!/usr/bin/env python3
"""Serial matched-lane runner for the unqualified product05 clipped diagnostic.

This script intentionally does not turn successful execution, tally closure, or
lane agreement into a transport qualification claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import h5py
import numpy as np


DEFAULT_CROSS_SECTIONS = Path("/mnt/c/Users/joshu/Documents/2026_DPA/openc-hts-dpa/.data/openmc/cross_sections.xml")
XML_NAMES = ("geometry.xml", "materials.xml", "tallies.xml", "settings.xml")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_named_paths(values: list[str], option: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{option} requires name=/absolute/path")
        name, raw_path = value.split("=", 1)
        path = Path(raw_path)
        if not name or name in result or not path.is_absolute() or not path.is_file():
            raise ValueError(f"invalid {option}: {value}")
        result[name] = path
    return result


def model_xml_directory(model: Path) -> Path:
    candidate = model / "xml" if (model / "xml").is_dir() else model
    if not candidate.is_dir() or any(not (candidate / name).is_file() for name in XML_NAMES):
        raise ValueError("--model must be an exported product05 model directory or its xml directory")
    return candidate


def tally_bins(xml_directory: Path) -> list[int]:
    text = ET.parse(xml_directory / "tallies.xml").findtext("filter/bins")
    if not text:
        raise ValueError("tallies.xml lacks the exported per-cell filter bins")
    return [int(value) for value in text.split()]


def validate_absolute_hdf_bindings(xml_directory: Path) -> list[str]:
    bindings = [surface.attrib["data_file"] for surface in ET.parse(xml_directory / "geometry.xml").findall("surface[@data_file]")]
    if not bindings or any(not (Path(binding).is_absolute() or binding.startswith("/")) for binding in bindings):
        raise ValueError("geometry.xml must retain absolute external HDF data_file bindings")
    return bindings


def hdf_binding_hashes(bindings: list[str]) -> dict[str, str]:
    paths = [Path(binding) for binding in bindings]
    if any(not path.is_file() for path in paths):
        raise ValueError("an absolute external HDF binding does not exist")
    return {str(path): sha256(path) for path in paths}


def resolved_openmc_library(binary: Path, requested_library: Path) -> dict[str, str]:
    """Verify the ELF loader will use the requested libopenmc before launch."""
    environment = dict(os.environ, LD_LIBRARY_PATH=str(requested_library.parent))
    probe = subprocess.run(["ldd", str(binary)], env=environment, text=True, capture_output=True, check=False)
    if probe.returncode != 0:
        raise RuntimeError(f"ldd failed for {binary}: {probe.stderr.strip()}")
    match = re.search(r"libopenmc\.so(?:\.\d+)*\s+=>\s+(\S+)", probe.stdout)
    if not match:
        raise RuntimeError(f"ldd did not resolve libopenmc.so for {binary}")
    actual = Path(match.group(1)).resolve()
    expected = requested_library.resolve()
    if actual != expected:
        raise RuntimeError(f"ldd resolved {actual}, not requested {expected}")
    return {"requested": str(expected), "resolved": str(actual), "ld_library_path": environment["LD_LIBRARY_PATH"], "ldd": probe.stdout}


def prepare_run_folder(source_xml: Path, run_folder: Path, histories: int, seed: int) -> dict[str, str]:
    """Copy immutable XML inputs and make the sole settings edits for one run."""
    run_folder.mkdir(parents=True, exist_ok=False)
    hashes: dict[str, str] = {}
    for name in XML_NAMES:
        source, destination = source_xml / name, run_folder / name
        shutil.copyfile(source, destination)
        if name != "settings.xml":
            hashes[name] = sha256(destination)
            if hashes[name] != sha256(source):
                raise RuntimeError(f"immutable input copy mismatch: {name}")
    settings_path = run_folder / "settings.xml"
    tree = ET.parse(settings_path)
    root = tree.getroot()
    for tag, value in (("particles", histories), ("seed", seed)):
        element = root.find(tag)
        if element is None:
            element = ET.SubElement(root, tag)
        element.text = str(value)
    ET.indent(root, space="  ")
    tree.write(settings_path, encoding="utf-8", xml_declaration=True)
    hashes["settings.xml"] = sha256(settings_path)
    return hashes


def statepoint_summary(path: Path) -> dict[str, object]:
    with h5py.File(path, "r") as state:
        def scalar(name: str) -> int | None:
            return int(state[name][()]) if name in state else None
        result: dict[str, object] = {
            "statepoint_sha256": sha256(path), "current_batch": scalar("current_batch"),
            "n_particles": scalar("n_particles"), "n_batches": scalar("n_batches"),
            "n_realizations": scalar("n_realizations"),
        }
        if "global_tallies" in state and state["global_tallies"].shape[0] > 3:
            result["leakage"] = float(state["global_tallies"][3, 1])
        if "tallies/tally 1/results" in state:
            result["cell_flux"] = state["tallies/tally 1/results"][..., 0].reshape(-1).astype(float).tolist()
        if "tallies/tally 2/results" in state:
            result["global_flux"] = float(state["tallies/tally 2/results"][0, 0, 0])
        result["runtime_seconds"] = {name: float(state["runtime"][name][()]) for name in state["runtime"]} if "runtime" in state else None
        cells = result.get("cell_flux")
        global_flux = result.get("global_flux")
        if cells is not None and global_flux is not None:
            result["flux_closure_absolute"] = abs(float(np.sum(cells)) - float(global_flux))
        active = None if result["runtime_seconds"] is None else result["runtime_seconds"].get("active batches")
        result["histories_per_active_second"] = None if active is None or active <= 0.0 else float(result["n_particles"] / active)
    required = ("leakage", "cell_flux", "global_flux", "flux_closure_absolute", "runtime_seconds", "histories_per_active_second")
    errors = [key for key in required if result.get(key) is None]
    for key in ("leakage", "global_flux", "flux_closure_absolute", "histories_per_active_second"):
        if key in result and result[key] is not None and not np.isfinite(float(result[key])):
            errors.append(key + ":nonfinite")
    if result.get("cell_flux") is not None and not np.isfinite(np.asarray(result["cell_flux"], dtype=float)).all():
        errors.append("cell_flux:nonfinite")
    if result.get("runtime_seconds") is not None and (not result["runtime_seconds"] or not all(np.isfinite(value) for value in result["runtime_seconds"].values())):
        errors.append("runtime_seconds:invalid")
    if result.get("n_realizations") in (None, 0):
        errors.append("n_realizations")
    result["metrics_valid"] = not errors
    result["metric_errors"] = errors
    result["closure_checked"] = result.get("flux_closure_absolute") is not None
    return result


def warning_lines(stdout: Path, stderr: Path) -> list[str]:
    pattern = re.compile(r"(?:warning|lost particle|maximum number of events)", re.IGNORECASE)
    return [line.rstrip() for path in (stdout, stderr) for line in path.read_text(errors="replace").splitlines() if pattern.search(line)]


def compare_attempts(attempts: list[dict[str, object]], tolerance: float, required_lane_names: set[str], baseline_lane: str) -> list[dict[str, object]]:
    by_seed: dict[int, list[dict[str, object]]] = {}
    for attempt in attempts:
        by_seed.setdefault(int(attempt["seed"]), []).append(attempt)
    comparisons: list[dict[str, object]] = []
    for seed, rows in sorted(by_seed.items()):
        completed = {str(row["lane"]): row for row in rows if row.get("completion") == "COMPLETE" and row.get("statepoint", {}).get("metrics_valid")}
        comparison: dict[str, object] = {"seed": seed, "baseline_lane": baseline_lane, "status": "BLOCKED_INCOMPLETE", "candidate_disagreement_count": None}
        if set(completed) != required_lane_names or baseline_lane not in completed:
            comparisons.append(comparison)
            continue
        baseline = completed[baseline_lane]["statepoint"]
        failures: list[dict[str, object]] = []
        for lane in sorted(required_lane_names - {baseline_lane}):
            row = completed[lane]
            current = row["statepoint"]
            for key in ("global_flux", "leakage"):
                if key not in baseline or key not in current:
                    failures.append({"lane": row["lane"], "metric": key, "reason": "missing"})
                elif abs(float(baseline[key]) - float(current[key])) > tolerance:
                    failures.append({"lane": row["lane"], "metric": key, "baseline": baseline[key], "candidate": current[key]})
            left, right = baseline.get("cell_flux"), current.get("cell_flux")
            if baseline.get("cell_bins") != current.get("cell_bins"):
                failures.append({"lane": row["lane"], "metric": "cell_bins", "reason": "identity_mismatch"})
            elif left is None or right is None or len(left) != len(right):
                failures.append({"lane": row["lane"], "metric": "cell_flux", "reason": "missing_or_shape"})
            else:
                for index, (a, b) in enumerate(zip(left, right)):
                    if abs(float(a) - float(b)) > tolerance:
                        failures.append({"lane": row["lane"], "metric": "cell_flux", "bin": index, "baseline": a, "candidate": b})
        comparison.update(status="AGREE" if not failures else "CANDIDATE_DISAGREEMENT", candidate_disagreement_count=len(failures), differences=failures)
        comparisons.append(comparison)
    return comparisons


def run_campaign(*, model: Path, lanes: dict[str, Path], libraries: dict[str, Path], output: Path,
                 histories: int, seeds: list[int], timeout: int, debug: bool, tolerance: float,
                 cross_sections: Path = DEFAULT_CROSS_SECTIONS, baseline_lane: str = "exact") -> dict[str, object]:
    if output.exists():
        raise FileExistsError("--output must not already exist")
    if histories <= 0 or timeout <= 0 or tolerance < 0 or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("histories/timeout/tolerance/seeds are invalid")
    if set(lanes) != set(libraries) or baseline_lane not in lanes or not cross_sections.is_file():
        raise ValueError("every --lane needs one --library and OPENMC_CROSS_SECTIONS must exist")
    xml = model_xml_directory(model)
    bindings = validate_absolute_hdf_bindings(xml)
    binding_hashes = hdf_binding_hashes(bindings)
    bins = tally_bins(xml)
    loader_checks = {name: resolved_openmc_library(binary, libraries[name]) for name, binary in lanes.items()}
    output.mkdir(parents=True)
    immutable_hashes = {name: sha256(xml / name) for name in XML_NAMES if name != "settings.xml"}
    receipt: dict[str, object] = {
        "schema": "stellarcsg.product06.compare-transport/v1", "status": "UNQUALIFIED_CLIPPED_DIAGNOSTIC_EXPERIMENT",
        "claim_boundary": "Exit code, closure, and lane agreement are recorded evidence only; none qualifies transport, periodic symmetry, or recovered throughput.",
        "model_xml": str(xml.resolve()), "immutable_xml_sha256": immutable_hashes, "hdf_bindings_sha256": binding_hashes,
        "cross_sections": str(cross_sections), "cross_sections_sha256": sha256(cross_sections),
        "lanes": {name: {"binary": str(binary), "binary_sha256": sha256(binary), "library": str(libraries[name]), "library_sha256": sha256(libraries[name]), "loader": loader_checks[name]} for name, binary in lanes.items()},
        "attempts": [], "tolerance_absolute": tolerance,
    }
    for seed_index, seed in enumerate(seeds):
        schedule = list(lanes)
        if seed_index % 2:
            schedule.reverse()
        for lane in schedule:
            folder = output / f"seed-{seed}" / lane
            input_hashes = prepare_run_folder(xml, folder, histories, seed)
            for name, expected in immutable_hashes.items():
                if input_hashes[name] != expected:
                    raise RuntimeError("lane changed immutable XML")
            stdout, stderr = folder / "stdout.txt", folder / "stderr.txt"
            env = dict(os.environ, OMP_NUM_THREADS="1", LD_LIBRARY_PATH=str(libraries[lane].parent),
                       OPENMC_CROSS_SECTIONS=str(cross_sections))
            command = [str(lanes[lane])]
            if debug:
                command.append("-g")
            attempt: dict[str, object] = {"lane": lane, "seed": seed, "command": command, "input_sha256": input_hashes,
                                            "environment": {key: env[key] for key in ("OMP_NUM_THREADS", "LD_LIBRARY_PATH", "OPENMC_CROSS_SECTIONS")}, "started_unix": time.time()}
            began = time.monotonic()
            try:
                with stdout.open("w") as out, stderr.open("w") as err:
                    process = subprocess.run(command, cwd=folder, env=env, stdout=out, stderr=err, timeout=timeout)
                attempt["exit_code"] = process.returncode
            except subprocess.TimeoutExpired:
                attempt["timeout"] = True
            attempt["runtime_seconds"] = time.monotonic() - began
            attempt.update(stdout=stdout.name, stderr=stderr.name, warnings=warning_lines(stdout, stderr))
            try:
                attempt["hdf_bindings_unchanged"] = hdf_binding_hashes(bindings) == binding_hashes
            except (OSError, ValueError) as error:
                attempt["hdf_bindings_unchanged"] = False
                attempt["hdf_binding_error"] = str(error)
            statepoints = sorted(folder.glob("statepoint.*.h5"))
            if statepoints:
                attempt["statepoint"] = statepoint_summary(statepoints[-1])
                attempt["statepoint"]["cell_bins"] = bins
                if len(attempt["statepoint"].get("cell_flux", [])) != len(bins):
                    attempt["statepoint"]["metrics_valid"] = False
                    attempt["statepoint"]["metric_errors"].append("cell_flux:bin_count")
            state = attempt.get("statepoint", {})
            attempt["completion"] = "COMPLETE" if attempt.get("exit_code") == 0 and attempt["hdf_bindings_unchanged"] and state.get("current_batch") == state.get("n_batches") and state.get("n_particles") == histories and state.get("metrics_valid") and state.get("closure_checked") else "INCOMPLETE"
            attempt["finished_unix"] = time.time()
            receipt["attempts"].append(attempt)
            (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    receipt["comparisons"] = compare_attempts(receipt["attempts"], tolerance, set(lanes), baseline_lane)
    receipt["candidate_disagreement_count"] = sum(int(row["candidate_disagreement_count"] or 0) for row in receipt["comparisons"])
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--lane", action="append", required=True, metavar="NAME=/ABS/BINARY")
    parser.add_argument("--library", action="append", required=True, metavar="NAME=/ABS/LIBOPENMC.SO")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--histories", type=int, default=64)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17, 19, 23])
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--absolute-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--cross-sections", type=Path, default=DEFAULT_CROSS_SECTIONS)
    parser.add_argument("--baseline-lane", default="exact")
    args = parser.parse_args()
    result = run_campaign(model=args.model, lanes=parse_named_paths(args.lane, "--lane"), libraries=parse_named_paths(args.library, "--library"),
                          output=args.output, histories=args.histories, seeds=args.seeds, timeout=args.timeout, debug=args.debug,
                          tolerance=args.absolute_tolerance, cross_sections=args.cross_sections, baseline_lane=args.baseline_lane)
    print(json.dumps({"output": str(args.output), "attempts": len(result["attempts"]), "candidate_disagreement_count": result["candidate_disagreement_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
