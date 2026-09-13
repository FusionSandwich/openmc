#!/usr/bin/env python3
"""Neutral command harness for matched StellarCSG A/B benchmark blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summary(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("samples must be finite and positive")
    ordered = sorted(values)
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive") if len(ordered) > 1 else ordered * 3
    mean = statistics.fmean(ordered)
    return {
        "median": statistics.median(ordered),
        "mean": mean,
        "iqr": quartiles[2] - quartiles[0],
        "coefficient_of_variation": (
            statistics.pstdev(ordered) / mean if len(ordered) > 1 and mean else 0.0
        ),
    }


def paired_bootstrap_ratio(
    numerator: list[float], denominator: list[float], *, seed: int, samples: int = 20000
) -> list[float]:
    if len(numerator) != len(denominator) or not numerator:
        raise ValueError("paired samples must be nonempty and equal length")
    if any(not math.isfinite(value) or value <= 0 for value in numerator + denominator):
        raise ValueError("ratio samples must be finite and positive")
    if samples < 1:
        raise ValueError("bootstrap samples must be positive")
    rng = random.Random(seed)
    size = len(numerator)
    ratios = []
    for _ in range(samples):
        indices = [rng.randrange(size) for _ in range(size)]
        ratios.append(
            statistics.median(numerator[index] for index in indices)
            / statistics.median(denominator[index] for index in indices)
        )
    ratios.sort()
    low = ratios[math.floor(0.025 * (samples - 1))]
    high = ratios[math.ceil(0.975 * (samples - 1))]
    return [low, high]


def schedule(method_ids: list[str], repetitions: int, policy: str, seed: int) -> list[list[str]]:
    if repetitions < 7:
        raise ValueError("qualification blocks require at least seven repetitions")
    if len(set(method_ids)) != len(method_ids) or not method_ids:
        raise ValueError("method ids must be nonempty and unique")
    rng = random.Random(seed)
    result: list[list[str]] = []
    if policy == "balanced":
        base = list(method_ids)
        rng.shuffle(base)
        for index in range(repetitions):
            offset = index % len(base)
            row = base[offset:] + base[:offset]
            if (index // len(base)) % 2:
                row.reverse()
            result.append(row)
    elif policy == "randomized":
        for _ in range(repetitions):
            row = list(method_ids)
            rng.shuffle(row)
            result.append(row)
    else:
        raise ValueError("order_policy must be balanced or randomized")
    return result


def validate_campaign(campaign: dict[str, Any]) -> None:
    protocol = campaign["protocol"]
    if int(protocol["warmups"]) < 1:
        raise ValueError("at least one warm-up is required")
    if int(protocol["measured_repetitions"]) < 7:
        raise ValueError("at least seven measured repetitions are required")
    if int(protocol["thread_count"]) < 1:
        raise ValueError("thread_count must be positive")
    common = campaign["common_artifacts"]
    for required in ("source_geometry", "source_bank", "settings"):
        if required not in common:
            raise ValueError(f"missing common artifact: {required}")
    for name, artifact in common.items():
        path = Path(artifact["path"])
        actual = sha256_file(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"{name} hash mismatch: expected {artifact['sha256']}, got {actual}")
    ids = []
    for method in campaign["methods"]:
        ids.append(method["id"])
        if not isinstance(method["command"], list) or not method["command"]:
            raise ValueError("command must be a nonempty argument list")
        if not Path(method["command"][0]).is_absolute():
            raise ValueError("command executable must be an absolute path")
        for required in ("binary", "compiled_geometry"):
            if required not in method["artifacts"]:
                raise ValueError(f"{method['id']} missing artifact: {required}")
        executable = Path(method["command"][0]).resolve(strict=True)
        binary = Path(method["artifacts"]["binary"]["path"]).resolve(strict=True)
        if executable != binary:
            raise ValueError(f"{method['id']} binary artifact does not bind command executable")
        for required in ("build_commit", "harness_commit", "hardware", "cpu_affinity", "thread_count", "libraries"):
            if required not in method["metadata"]:
                raise ValueError(f"{method['id']} missing metadata: {required}")
        if method["metadata"]["thread_count"] != protocol["thread_count"]:
            raise ValueError("method thread_count differs from common protocol")
        for name in ("build_commit", "harness_commit"):
            if not re.fullmatch(r"[0-9a-f]{40}", method["metadata"][name]):
                raise ValueError(f"{name} must be a full commit SHA")
        for library in method["metadata"]["libraries"]:
            if sha256_file(Path(library["path"])) != library["sha256"]:
                raise ValueError(f"{method['id']} linked library hash mismatch: {library['path']}")
        for name, artifact in method["artifacts"].items():
            path = Path(artifact["path"])
            actual = sha256_file(path)
            if actual != artifact["sha256"]:
                raise ValueError(
                    f"{method['id']} {name} hash mismatch: expected {artifact['sha256']}, got {actual}"
                )
    if campaign["sentinel_method"] not in ids:
        raise ValueError("sentinel_method must name one compared method")
    sentinel = next(method for method in campaign["methods"] if method["id"] == campaign["sentinel_method"])
    if sentinel["metadata"].get("surface_method") != "builtin_ztorus":
        raise ValueError("sentinel must declare builtin_ztorus")
    metadata = [method["metadata"] for method in campaign["methods"]]
    for field in ("hardware", "cpu_affinity", "harness_commit"):
        if len({str(item[field]) for item in metadata}) != 1:
            raise ValueError(f"unmatched {field}")
    dagmc = [method for method in campaign["methods"]
             if method["metadata"].get("surface_method") in ("ordinary_dagmc", "double_down_embree")]
    if dagmc:
        if any("h5m" not in method["artifacts"] for method in dagmc):
            raise ValueError("DAGMC methods require an h5m artifact")
        if len({method["artifacts"]["h5m"]["sha256"] for method in dagmc}) != 1:
            raise ValueError("ordinary DAGMC and Double Down require identical H5M bytes")
    schedule(ids, int(protocol["measured_repetitions"]), protocol["order_policy"], int(protocol["seed"]))


def invoke(method: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        method["command"],
        cwd=method.get("cwd"),
        env={**os.environ, **method.get("environment", {})},
        check=False,
        capture_output=True,
        text=True,
        timeout=method.get("timeout_seconds", 300),
    )
    wall = time.perf_counter() - started
    result = {"harness_wall_seconds": wall, "stdout": completed.stdout,
              "stderr": completed.stderr, "return_code": completed.returncode,
              "valid": False, "invalid_reasons": [], "payload": None}
    if completed.returncode:
        result["invalid_reasons"].append(f"command exited with code {completed.returncode}")
    try:
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise ValueError("command output must be an object")
        result["payload"] = payload
        for name in ("histories_per_s", "active_transport_seconds", "total_wall_seconds"):
            value = payload.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if payload["total_wall_seconds"] < payload["active_transport_seconds"]:
            raise ValueError("total wall time is smaller than active transport time")
        if payload.get("contaminated") or payload.get("valid") is False:
            raise ValueError(f"command marked attempt invalid: {payload.get('invalid_reason', 'unspecified')}")
    except (ValueError, TypeError, OverflowError) as error:
        result["invalid_reasons"].append(str(error))
    result["valid"] = not result["invalid_reasons"]
    return result


def run_campaign(campaign: dict[str, Any], *, journal_path: Path | None = None) -> dict[str, Any]:
    validate_campaign(campaign)
    methods = {method["id"]: method for method in campaign["methods"]}
    protocol = campaign["protocol"]
    method_ids = list(methods)
    repetitions: dict[str, list[dict[str, Any]]] = {method_id: [] for method_id in method_ids}
    orders = schedule(
        method_ids,
        int(protocol["measured_repetitions"]),
        protocol["order_policy"],
        int(protocol["seed"]),
    )
    attempts = []
    # Exclusive creation prevents a restarted campaign from overwriting evidence.
    journal = journal_path.open("x", encoding="utf-8") if journal_path else None

    def retain(record):
        if journal:
            journal.write(json.dumps(record, allow_nan=False) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

    def attempt(method_id, phase, index, order_index):
        identity = {"method_id": method_id, "phase": phase, "index": index,
                    "order_index": order_index, "attempt_id": len(attempts)}
        retain({"event": "started", **identity})
        try:
            validate_campaign(campaign)
            result = invoke(methods[method_id])
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result = {"valid": False, "invalid_reasons": [str(error)], "payload": None}
            if isinstance(error, subprocess.TimeoutExpired):
                result.update(stdout=str(error.stdout or ""), stderr=str(error.stderr or ""))
        try:
            validate_campaign(campaign)
        except (OSError, ValueError) as error:
            result["valid"] = False
            result["invalid_reasons"].append(f"post-attempt drift: {error}")
        # Preserve nonstandard JSON tokens in stdout; parsed nonfinite values cannot
        # enter the strict journal or summary.
        result = json.loads(json.dumps(result), parse_constant=lambda token: None)
        result.update(identity)
        attempts.append(result)
        if phase == "measured":
            repetitions[method_id].append(result)
        retain({"event": "finished", **result})

    try:
        retain({"event": "campaign", "schema": "stellarcsg.neutral-command-campaign/v2", "campaign": campaign})
        for index in range(int(protocol["warmups"])):
            for order_index, method_id in enumerate(method_ids):
                attempt(method_id, "warmup", index, order_index)
        for repetition_index, row in enumerate(orders):
            for order_index, method_id in enumerate(row):
                attempt(method_id, "measured", repetition_index, order_index)
    finally:
        if journal:
            journal.close()

    sentinel = campaign["sentinel_method"]
    aggregates: dict[str, Any] = {}
    for method_id, rows in repetitions.items():
        pairs = [(row, control) for row, control in zip(rows, repetitions[sentinel])
                 if row["valid"] and control["valid"]]
        values = [float(row["payload"]["histories_per_s"]) for row, _ in pairs]
        sentinel_values = [float(row["payload"]["histories_per_s"]) for _, row in pairs]
        aggregates[method_id] = {
            **(summary(values) if values else {}),
            "valid_pair_count": len(pairs),
            "pairing": "same scheduled repetition index; common source does not imply identical trajectories",
            "ratio_numerator": method_id,
            "ratio_denominator": sentinel,
            "ratio_to_sentinel": statistics.median(values) / statistics.median(sentinel_values) if values else None,
            "bootstrap_ratio_interval_95": paired_bootstrap_ratio(
                values, sentinel_values, seed=int(protocol["seed"])
            ) if len(pairs) >= 7 else None,
        }
    return {
        "schema": "stellarcsg.neutral-command-campaign/v2",
        "gate_status": "NOT_RUN" if all(row["valid"] for row in attempts) else "BLOCKED",
        "qualification_note": "Timing envelope only; independent geometry eligibility and gate evaluation are required.",
        "durable_journal": str(journal_path) if journal_path else None,
        "case_id": campaign["case_id"],
        "protocol": protocol,
        "common_artifacts": campaign["common_artifacts"],
        "method_metadata": {method_id: methods[method_id]["metadata"] for method_id in method_ids},
        "methods": campaign["methods"],
        "attempts": attempts,
        "execution_order": orders,
        "repetitions": repetitions,
        "aggregates": aggregates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    campaign = json.loads(args.campaign.read_text(encoding="utf-8"))
    validate_campaign(campaign)
    if args.dry_run:
        protocol = campaign["protocol"]
        result = {
            "valid": True,
            "execution_order": schedule(
                [method["id"] for method in campaign["methods"]],
                int(protocol["measured_repetitions"]),
                protocol["order_policy"],
                int(protocol["seed"]),
            ),
        }
    else:
        if args.output is None:
            parser.error("--output is required unless --dry-run is used")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            raise FileExistsError(args.output)
        result = run_campaign(campaign, journal_path=args.output.with_suffix(args.output.suffix + ".attempts.jsonl"))
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
