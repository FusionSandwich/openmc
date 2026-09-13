#!/usr/bin/env python3
"""Run a bounded, CPU-0, matched cold-query campaign for swept filter modes.

This is a qualification recorder, not transport.  It invokes the standalone
``test_swept_filtered`` harness using its immutable 64-ray bank.  The default
eight-ray pilot deliberately includes broad misses; it is unsuitable for a
claim about hit-heavy transport throughput.  Use ``--count 16`` only after the
pilot has completed cleanly.  Seven measured repetitions plus one warm-up are
required, and all attempted records are durable even when a mode fails.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time


HARNESS_PATH = Path(__file__).parents[1] / "benchmarks" / "dual_track_harness.py"
HARNESS_SPEC = importlib.util.spec_from_file_location("neutral_harness", HARNESS_PATH)
HARNESS = importlib.util.module_from_spec(HARNESS_SPEC)
HARNESS_SPEC.loader.exec_module(HARNESS)

MODES = (0, 1, 2)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = fraction*(len(ordered) - 1)
    low, high = math.floor(rank), math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low])*(rank - low)


def distribution(values: list[float]) -> dict[str, float] | None:
    if not values or any(not math.isfinite(value) or value < 0 for value in values):
        return None
    return {"mean": statistics.fmean(values), "median": statistics.median(values),
            "p95": percentile(values, .95), "p99": percentile(values, .99),
            "samples": len(values)}


def artifact(path: Path) -> dict:
    resolved = path.resolve(strict=True)
    return {"path": str(path.absolute()), "resolved_path": str(resolved),
            "sha256": sha256(resolved)}


def parse_capture(path: Path, count: int) -> tuple[list[dict], dict]:
    rows, summary = [], None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        payload = json.loads(line)
        if payload.get("kind") == "ray":
            rows.append(payload)
        elif payload.get("kind") == "summary":
            summary = payload
    if len(rows) != count or summary is None:
        raise ValueError("capture lacks the requested complete frozen ray prefix")
    if [row.get("index") for row in rows] != list(range(count)):
        raise ValueError("capture ray indices drifted")
    return rows, summary


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def compare_rows(reference: list[dict], candidate: list[dict]) -> list[str]:
    errors = []
    for left, right in zip(reference, candidate):
        identity = ("index", "category", "origin", "direction", "coincident", "transformed")
        if any(left.get(key) != right.get(key) for key in identity):
            errors.append(f"frozen input drift at ray {left.get('index')}")
            continue
        # BLOCKED/no-hit and solver disposition are semantic outcomes, so their
        # identity must be exact rather than approximated numerically.
        disposition = ("found", "state", "root_kind", "solver_path", "fallback_reason")
        if any(left.get(key) != right.get(key) for key in disposition):
            errors.append(f"disposition mismatch at ray {left['index']}")
            continue
        if left.get("found"):
            for key in ("distance", "residual"):
                if not finite(left.get(key)) or not finite(right.get(key)) or abs(left[key] - right[key]) > 2.e-8:
                    errors.append(f"{key} mismatch at ray {left['index']}")
    return errors


def optional_filter_metrics(rows: list[dict]) -> dict:
    diagnostics = [row.get("diagnostics", {}) for row in rows if isinstance(row.get("diagnostics"), dict)]
    result = {}
    for name in ("floating_excluded_spans", "polynomial_excluded_spans", "exact_candidate_spans",
                 "long_monotone_attempted_spans", "monotone_resolved_spans", "sturm_fallback_spans"):
        values = [item[name] for item in diagnostics if finite(item.get(name))]
        if values:
            result[name] = sum(values)
    exact = [item["exact_query_nanoseconds"] for item in diagnostics
             if finite(item.get("exact_query_nanoseconds"))]
    candidate = [item["exact_candidate_nanoseconds"] for item in diagnostics
                 if finite(item.get("exact_candidate_nanoseconds"))]
    monotone = [item["monotone_nanoseconds"] for item in diagnostics
                if finite(item.get("monotone_nanoseconds"))]
    candidate_spans = [item["exact_candidate_spans"] for item in diagnostics
                       if finite(item.get("exact_candidate_spans"))]
    total_query_ns = [row["ns"] for row in rows if finite(row.get("ns"))]
    timer_available = any("exact_query_nanoseconds" in item for item in diagnostics)
    result["fallback_time_fraction"] = (sum(exact)/sum(total_query_ns)
                                        if timer_available and total_query_ns else None)
    result["exact_path_observed"] = (any(value > 0 for value in exact)
                                     or any(value > 0 for value in candidate_spans))
    if exact:
        result["exact_query_nanoseconds"] = sum(exact)
    if candidate:
        result["exact_candidate_nanoseconds"] = sum(candidate)
        result["candidate_time_fraction_within_exact"] = sum(candidate)/sum(exact) if sum(exact) else None
    monotone_timer_available = any("monotone_nanoseconds" in item for item in diagnostics)
    result["monotone_time_fraction"] = (sum(monotone)/sum(total_query_ns)
                                         if monotone_timer_available and total_query_ns else None)
    if monotone:
        result["monotone_nanoseconds"] = sum(monotone)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="new immutable output directory")
    parser.add_argument("--count", type=int, choices=(8, 16), default=8)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.repeats < 7:
        parser.error("at least seven measured repetitions are required")
    binary = args.binary.resolve(strict=True)
    if not os.access(binary, os.X_OK):
        raise ValueError(f"binary is not executable: {binary}")
    if args.output.exists():
        raise FileExistsError(args.output)
    if not hasattr(os, "sched_setaffinity"):
        raise RuntimeError("this campaign requires Linux sched_setaffinity for explicit CPU 0")
    os.sched_setaffinity(0, {args.cpu})
    if os.sched_getaffinity(0) != {args.cpu}:
        raise RuntimeError("unable to bind campaign to the requested one CPU")
    schedule = HARNESS.schedule([str(mode) for mode in MODES], args.repeats, "balanced", 713)
    source_root = Path(__file__).parents[1]
    artifacts = {"binary": artifact(binary), "campaign_script": artifact(Path(__file__)),
                 "neutral_harness": artifact(HARNESS_PATH),
                 "source_cpp": artifact(source_root / "tests" / "test_swept_filtered.cpp"),
                 "root_solver_header": artifact(source_root / "include" / "stellarcsg" / "root_solver.hpp"),
                 "compiled_swept_header": artifact(source_root / "include" / "stellarcsg" / "compiled_swept_surface.hpp"),
                 "floating_filter_header": artifact(source_root / "src" / "swept_floating_filter.hpp")}
    manifest = {"schema": "stellarcsg.swept-filter-cold-query/v1", "artifacts": artifacts,
                "cpu_affinity": [args.cpu], "modes": list(MODES),
                "count": args.count, "warmups": 1, "measured_repetitions": args.repeats,
                "schedule": schedule, "profile": True,
                "scope": "cold exact query only; no transport and no application memoization",
                "broad_miss_note": "The interleaved pilot includes broad misses and does not model hit-heavy transport."}
    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0
    args.output.mkdir(parents=True, exist_ok=False)
    journal_path = args.output / "attempts.jsonl"
    attempts = []
    with journal_path.open("x", encoding="utf-8") as journal:
        def retain(record: dict) -> None:
            journal.write(json.dumps(record, allow_nan=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        retain({"event": "campaign", "manifest": manifest})
        def invoke(mode: int, phase: str, repetition: int, order: int) -> dict:
            directory = args.output / f"{phase}-{repetition:02d}-{order:02d}-mode{mode}"
            directory.mkdir()
            stdout, stderr = directory / "stdout.jsonl", directory / "stderr.txt"
            identity = {"mode": mode, "phase": phase, "repetition": repetition,
                        "order": order, "directory": str(directory)}
            pre_binary_sha = sha256(binary)
            retain({"event": "started", **identity,
                    "command": [str(binary), "--mode", str(mode), "--count", str(args.count),
                                "--profile", "--skip-controls"],
                    "binary_sha256_before": pre_binary_sha})
            record = {**identity, "valid": False, "invalid_reasons": [],
                      "stdout": str(stdout), "stderr": str(stderr), "return_code": None,
                      "rows": None, "summary": None, "wall_seconds": None,
                      "binary_sha256_before": pre_binary_sha, "binary_sha256_after": None}
            started = time.perf_counter()
            try:
                with stdout.open("xb") as out, stderr.open("xb") as err:
                    completed = subprocess.run(
                        [str(binary), "--mode", str(mode), "--count", str(args.count),
                         "--profile", "--skip-controls"], cwd=directory, stdout=out, stderr=err,
                        check=False, timeout=args.timeout)
                record["return_code"] = completed.returncode
                if completed.returncode:
                    record["invalid_reasons"].append(f"exit code {completed.returncode}")
                rows, summary = parse_capture(stdout, args.count)
                record["rows"], record["summary"] = rows, summary
                if summary.get("failures") or summary.get("blocked"):
                    record["invalid_reasons"].append("harness reported failures or blocked rays")
                if (summary.get("mode") != mode or not summary.get("profile")
                        or not summary.get("controls_skipped")):
                    record["invalid_reasons"].append("capture mode/profile identity drift")
                if any(not finite(row.get("ns")) or row["ns"] < 0 for row in rows):
                    record["invalid_reasons"].append("missing finite per-query ns")
            except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
                record["invalid_reasons"].append(str(error))
            record["binary_sha256_after"] = sha256(binary)
            if (record["binary_sha256_before"] != manifest["artifacts"]["binary"]["sha256"]
                    or record["binary_sha256_after"] != manifest["artifacts"]["binary"]["sha256"]):
                record["invalid_reasons"].append("binary hash drift")
            record["output_artifacts"] = [artifact(path) for path in (stdout, stderr) if path.exists()]
            record["wall_seconds"] = time.perf_counter() - started
            record["valid"] = not record["invalid_reasons"]
            retain({"event": "finished", **record})
            attempts.append(record)
            return record

        for order, mode_text in enumerate(MODES):
            mode = int(mode_text)
            invoke(mode, "warmup", 0, order)
        for repetition, row in enumerate(schedule):
            for order, mode_text in enumerate(row):
                invoke(int(mode_text), "measured", repetition, order)

    measured = {mode: [item for item in attempts if item["phase"] == "measured" and item["mode"] == mode]
                for mode in MODES}
    comparisons = []
    for repetition in range(args.repeats):
        sample = [next(item for item in measured[mode] if item["repetition"] == repetition) for mode in MODES]
        valid = all(item["valid"] and item["rows"] is not None for item in sample)
        errors = [] if valid else ["invalid attempt in matched repetition"]
        if valid:
            errors.extend(compare_rows(sample[0]["rows"], sample[1]["rows"]))
            errors.extend(compare_rows(sample[0]["rows"], sample[2]["rows"]))
        comparisons.append({"repetition": repetition, "valid": not errors, "errors": errors})
    aggregates = {}
    for mode, records in measured.items():
        rows = [row for record in records if record["valid"] for row in record["rows"]]
        repetition_means = [sum(row["ns"] for row in record["rows"])/args.count
                            for record in records if record["valid"]]
        category_costs = {category: distribution([row["ns"] for row in rows
                                                   if row.get("category") == category])
                          for category in sorted({row.get("category") for row in rows})}
        aggregates[str(mode)] = {"pooled_ray_ns_distribution": distribution([row["ns"] for row in rows]),
                                 "per_repetition_mean_ns_distribution": distribution(repetition_means),
                                 "per_category_ns_distribution": category_costs,
                                 "filter_metrics": optional_filter_metrics(rows),
                                 "valid_attempts": sum(record["valid"] for record in records),
                                 "retained_attempts": len(records)}
    ratios = []
    baseline = {record["repetition"]: sum(row["ns"] for row in record["rows"])/args.count
                for record in measured[0] if record["valid"]}
    for mode in (1, 2):
        changed = {record["repetition"]: sum(row["ns"] for row in record["rows"])/args.count
                   for record in measured[mode] if record["valid"]}
        indices = [index for index in range(args.repeats)
                   if index in baseline and index in changed and comparisons[index]["valid"]]
        old, new = [baseline[index] for index in indices], [changed[index] for index in indices]
        ratios.append({"baseline_mode": 0, "changed_mode": mode, "valid_pairs": len(indices),
                       "definition": "mode 0 ns/query divided by changed ns/query; >1 favors changed",
                       "paired_bootstrap_ratio_interval_95": HARNESS.paired_bootstrap_ratio(
                           old, new, seed=713) if len(old) >= 7 else None})
    final_artifacts = {name: artifact(Path(item["path"])) for name, item in artifacts.items()}
    artifact_drift = [name for name in artifacts
                      if final_artifacts[name]["sha256"] != artifacts[name]["sha256"]]
    result = {"manifest": manifest, "journal": str(journal_path), "attempts": attempts,
              "comparisons": comparisons, "aggregates": aggregates, "paired_ratios": ratios,
              "final_artifacts": final_artifacts, "artifact_drift": artifact_drift,
              "block_valid": (not artifact_drift and all(item["valid"] for item in attempts)
                              and all(item["valid"] for item in comparisons)),
              "qualification": "NOT_RUN"}
    with (args.output / "campaign.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"block_valid": result["block_valid"], "aggregates": aggregates}, indent=2))
    return 0 if result["block_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
