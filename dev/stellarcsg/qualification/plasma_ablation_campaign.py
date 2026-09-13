"""Retain matched periodic-kernel ablation evidence and a native host sentinel.

Linux/WSL only; run after the coordinator grants the exclusive benchmark slot.
Kernel ns/query and OpenMC sentinel histories/s remain separate measurements.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time


HARNESS_PATH = Path(__file__).parents[1] / "benchmarks/dual_track_harness.py"
SPEC = importlib.util.spec_from_file_location("neutral_harness", HARNESS_PATH)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def artifact(path):
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    return {"path": str(path), "resolved_path": str(resolved),
            "sha256": HARNESS.sha256_file(path)}


def linkage(binary, environment):
    result = subprocess.run(["/usr/bin/ldd", str(binary)], env=environment,
                            text=True, capture_output=True, check=True, timeout=20)
    if "not found" in result.stdout:
        raise ValueError(f"unresolved linkage for {binary}: {result.stdout}")
    paths = re.findall(r"(?:=>\s+)?(/[^\s()]+)", result.stdout)
    return [artifact(path) for path in sorted(set(paths)) if Path(path).is_file()]


def check_artifacts(records):
    errors = []
    for record in records:
        try:
            if str(Path(record["path"]).resolve(strict=True)) != record["resolved_path"]:
                errors.append(f"symlink target drift: {record['path']}")
            actual = HARNESS.sha256_file(Path(record["path"]))
            if actual != record["sha256"]:
                errors.append(f"hash drift: {record['path']}")
        except OSError as error:
            errors.append(str(error))
    return errors


def finite_positive(value):
    try:
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value) and value > 0)
    except OverflowError:
        return False


def read_capture(path):
    return [json.loads(line) for line in Path(path).read_text(
        encoding="utf-8-sig").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--wistell-file", type=Path, required=True)
    parser.add_argument("--dataset", default="/surfaces/wistell_d_lcfs")
    parser.add_argument("--sentinel-binary", type=Path, required=True)
    parser.add_argument("--sentinel-model", type=Path, required=True)
    parser.add_argument("--sentinel-libdir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-sha", default="4774434f10ab922411a0b3eefc243d07ea4adb17")
    parser.add_argument("--candidate-sha", default="1620263e1866e035ca293d270b10a193330dc104")
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--banks", type=int, default=128)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--seed", type=int, default=713)
    parser.add_argument("--order", choices=["balanced", "randomized"], default="balanced")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.banks <= 1000 or args.repetitions < 7:
        parser.error("banks must be 1..1000 and repetitions at least seven")
    for sha in (args.baseline_sha, args.candidate_sha):
        if not re.fullmatch("[0-9a-f]{40}", sha):
            parser.error("full source commit SHA required")

    environment = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    sentinel_environment = dict(environment)
    if args.sentinel_libdir:
        sentinel_environment["LD_LIBRARY_PATH"] = str(args.sentinel_libdir.resolve()) + (
            ":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else "")
    # Children inherit verified affinity; this process performs all orchestration
    # serially. This does not discover or stop unrelated host interference.
    os.sched_setaffinity(0, {args.cpu})
    if os.sched_getaffinity(0) != {args.cpu}:
        raise ValueError("unable to bind requested single CPU")

    replay_source = args.candidate_source / "dev/stellarcsg/tests/test_periodic_optimization.cpp"
    common = [artifact(__file__), artifact(HARNESS_PATH), artifact(replay_source),
              artifact(args.wistell_file), artifact(args.sentinel_model)]
    frozen = {}
    for case in ("helical", "wistell"):
        path = args.build_root / f"plasma-baseline-on-{case}-correctness-01.jsonl"
        common.append(artifact(path))
        frozen[case] = [row for row in read_capture(path) if row["kind"] == "ray"]
        if len(frozen[case]) != 256:
            raise ValueError(f"{case} frozen bank must contain 256 rays")

    methods = {}
    for case in ("helical", "wistell"):
        for version in ("baseline", "candidate"):
            source = args.baseline_source if version == "baseline" else args.candidate_source
            for counters in ("on", "off"):
                method_id = f"{case}-{version}-{counters}"
                build = args.build_root / f"plasma-{version}-{counters}"
                binary = (build / "periodic_optimization_replay_v2").resolve(strict=True)
                command = [str(binary)]
                if case == "wistell":
                    command += [str(args.wistell_file.resolve()), args.dataset]
                command += [str(args.banks)]
                methods[method_id] = dict(
                    case=case, version=version, counters=counters == "on",
                    command=command, units="ns/query",
                    declared_source_commit=(args.baseline_sha if version == "baseline"
                                            else args.candidate_sha),
                    artifacts=[artifact(binary), artifact(build / "libstellarcsg_reference.a"),
                               artifact(build / "CMakeCache.txt"),
                               artifact(source / "dev/stellarcsg/src/compiled_periodic_surface.cpp")],
                    libraries=linkage(binary, environment))
    sentinel = "native-ztorus-host-sentinel"
    binary = args.sentinel_binary.resolve(strict=True)
    methods[sentinel] = dict(case="native_ztorus", version="checkpoint", counters=False,
                            command=[str(binary)], units="histories/s",
                            artifacts=[artifact(binary)], libraries=linkage(binary, sentinel_environment))
    orders = HARNESS.schedule(list(methods), args.repetitions, args.order, args.seed)
    manifest = dict(
        schema="stellarcsg.plasma-kernel-ablation/v1", qualification="NOT_RUN",
        methods=methods, shared_artifacts=common, measured_orders=orders,
        warmup_order=orders[0], measured_repetitions=args.repetitions,
        banks_per_attempt=args.banks, cpu_affinity=sorted(os.sched_getaffinity(0)),
        environment={name: environment.get(name) for name in
                     ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "OPENMC_CROSS_SECTIONS")},
        sentinel_library_path=sentinel_environment.get("LD_LIBRARY_PATH"),
        hardware=dict(uname=list(os.uname()), logical_cpu_count=os.cpu_count()),
        source_bank="256 frozen rays per geometry; exact returned records checked against baseline capture",
        compiled_geometry=dict(wistell=artifact(args.wistell_file), helical=None),
        synthetic_geometry="in-memory coefficients defined by hashed replay source",
        correctness="sampled oracle only; inherited WISTELL BLOCKED rays remain unresolved",
        peak_rss_bytes=None, initialization_seconds=None,
        warnings=["No kernel/sentinel ratio; workloads differ.",
                  "Runtime artifacts verified, source commit identities supplied by coordinator Git preflight.",
                  "Measured seconds excludes separate query-tail pass and independent oracle.",
                  "Hashing and journaling occur outside measured kernel intervals; cache effects remain possible.",
                  "Unrelated desktop activity is not controlled or certified absent."])
    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return 0

    args.output.mkdir(parents=True, exist_ok=False)
    journal = (args.output / "attempts.jsonl").open("x", encoding="utf-8")
    attempts = []

    def retain(record):
        journal.write(json.dumps(record, allow_nan=False) + "\n")
        journal.flush()
        os.fsync(journal.fileno())

    def invoke(method_id, phase, index, order_index):
        method = methods[method_id]
        identity = dict(method_id=method_id, phase=phase, index=index, order_index=order_index)
        directory = args.output / f"{phase}-{index:02d}-{order_index:02d}-{method_id}"
        directory.mkdir(exist_ok=False)
        # Start is durable before any attempted invocation, even if drift is found.
        retain(dict(event="started", **identity, command=method["command"],
                    directory=str(directory), expected_hashes=common + method["artifacts"] + method["libraries"]))
        hashes = common + method["artifacts"] + method["libraries"]
        result = dict(**identity, valid=False, invalid_reasons=check_artifacts(hashes),
                      return_code=None, kernel_summary=None, sentinel_summary=None,
                      stdout_file=str(directory / "stdout.txt"), stderr_file=str(directory / "stderr.txt"))
        start = time.perf_counter()
        if not result["invalid_reasons"]:
            try:
                if method_id == sentinel:
                    target = directory / "model.xml"
                    shutil.copyfile(args.sentinel_model, target)
                    if HARNESS.sha256_file(target) != artifact(args.sentinel_model)["sha256"]:
                        raise ValueError("copied sentinel XML differs")
                with (directory / "stdout.txt").open("xb") as out, (directory / "stderr.txt").open("xb") as err:
                    completed = subprocess.run(method["command"], cwd=directory,
                        env=sentinel_environment if method_id == sentinel else environment,
                        stdout=out, stderr=err, timeout=120, check=False)
                result["return_code"] = completed.returncode
                if completed.returncode != 0:
                    result["invalid_reasons"].append(f"exit code {completed.returncode}")
                stdout = (directory / "stdout.txt").read_text(errors="replace")
                if method_id == sentinel:
                    rate = re.search(r"Calculation Rate(?: \(active\))?\s*=\s*([0-9.eE+-]+)", stdout)
                    active = re.search(r"Time in transport only\s*=\s*([0-9.eE+-]+)", stdout)
                    initialization = re.search(r"Total time for initialization\s*=\s*([0-9.eE+-]+)", stdout)
                    rate = float(rate.group(1)) if rate else None
                    if not finite_positive(rate):
                        result["invalid_reasons"].append("missing or invalid native sentinel throughput")
                    if re.search(r"WARNING.*lost particle|geometry error|overlapping cells", stdout, re.I):
                        result["invalid_reasons"].append("native sentinel reported geometry failure")
                    result["sentinel_summary"] = dict(histories_per_s=rate,
                        active_transport_seconds=float(active.group(1)) if active else None,
                        initialization_seconds=float(initialization.group(1)) if initialization else None)
                else:
                    payloads = [json.loads(line) for line in stdout.splitlines() if line.strip()]
                    rows = [row for row in payloads if row.get("kind") == "ray"]
                    summary = payloads[-1]
                    if summary.get("kind") != "summary" or rows != frozen[method["case"]]:
                        result["invalid_reasons"].append("frozen ray return records changed")
                    if summary.get("calls") != 256*args.banks or summary.get("repeats") != args.banks:
                        result["invalid_reasons"].append("wrong replay size")
                    if summary.get("counters_enabled") != method["counters"]:
                        result["invalid_reasons"].append("counter build identity mismatch")
                    if summary.get("repeat_mismatches") != 0 or summary.get("failures") != 0:
                        result["invalid_reasons"].append("kernel reported correctness/determinism failure")
                    digests = summary.get("return_digests", [])
                    if len(digests) != args.banks or len(set(digests)) != 1:
                        result["invalid_reasons"].append("return digest mismatch")
                    if not finite_positive(summary.get("seconds")) or not finite_positive(summary.get("ns_per_query")):
                        result["invalid_reasons"].append("invalid kernel timing")
                    result["kernel_summary"] = summary
            except (OSError, ValueError, IndexError, KeyError, AttributeError,
                    TypeError, OverflowError, subprocess.SubprocessError) as error:
                result["invalid_reasons"].append(str(error))
        result["harness_wall_seconds"] = time.perf_counter()-start
        result["invalid_reasons"].extend(check_artifacts(hashes))
        result["valid"] = not result["invalid_reasons"]
        # Invalid non-standard numeric tokens are retained in raw stdout; never
        # emit them as misleading JSON numbers in the journal.
        result = json.loads(json.dumps(result), parse_constant=lambda token: None)
        result["output_hashes"] = [artifact(directory / name) for name in ("stdout.txt", "stderr.txt")
                                   if (directory / name).exists()]
        retain(dict(event="finished", **result))
        attempts.append(result)

    try:
        retain(dict(event="campaign", manifest=manifest))
        for order_index, method_id in enumerate(orders[0]):
            invoke(method_id, "warmup", 0, order_index)
        for index, order in enumerate(orders):
            for order_index, method_id in enumerate(order):
                invoke(method_id, "measured", index, order_index)
    finally:
        journal.close()

    comparisons = []
    for case in ("helical", "wistell"):
        for instrumented in ("on", "off"):
            baseline = {row["index"]: row for row in attempts if row["phase"] == "measured"
                        and row["method_id"] == f"{case}-baseline-{instrumented}"}
            candidate = {row["index"]: row for row in attempts if row["phase"] == "measured"
                         and row["method_id"] == f"{case}-candidate-{instrumented}"}
            pairs = [(baseline[i], candidate[i]) for i in baseline
                     if baseline[i]["valid"] and candidate[i]["valid"]]
            old = [a["kernel_summary"]["ns_per_query"] for a, _ in pairs]
            new = [b["kernel_summary"]["ns_per_query"] for _, b in pairs]
            comparisons.append(dict(case=case, counters=instrumented, valid_pairs=len(pairs),
                baseline_ns=HARNESS.summary(old) if old else None,
                candidate_ns=HARNESS.summary(new) if new else None,
                ratio_definition="baseline ns/query divided by candidate ns/query; >1 means faster candidate",
                speed_ratio=statistics.median(old)/statistics.median(new) if old else None,
                paired_bootstrap_interval_95=HARNESS.paired_bootstrap_ratio(old, new, seed=args.seed)
                    if len(pairs) >= 7 else None))
    sentinel_values = [row["sentinel_summary"]["histories_per_s"] for row in attempts
                       if row["phase"] == "measured" and row["method_id"] == sentinel and row["valid"]]
    result = dict(manifest=manifest, attempts=attempts, comparisons=comparisons,
                  sentinel_histories_per_s=HARNESS.summary(sentinel_values) if sentinel_values else None,
                  block_valid=all(row["valid"] for row in attempts),
                  qualification="NOT_RUN")
    with (args.output / "campaign.json").open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write("\n")
    print(json.dumps(dict(block_valid=result["block_valid"], comparisons=comparisons), indent=2))
    return 0 if result["block_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
