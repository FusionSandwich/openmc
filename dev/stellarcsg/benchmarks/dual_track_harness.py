#!/usr/bin/env python3
"""Neutral command harness for matched StellarCSG A/B benchmark blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
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
    if not values:
        raise ValueError("cannot summarize an empty sample")
    ordered = sorted(values)
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
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
    if any(value <= 0 for value in denominator):
        raise ValueError("ratio denominator must be positive")
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
    for name, artifact in common.items():
        path = Path(artifact["path"])
        actual = sha256_file(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"{name} hash mismatch: expected {artifact['sha256']}, got {actual}")
    ids = []
    for method in campaign["methods"]:
        ids.append(method["id"])
        for name, artifact in method["artifacts"].items():
            path = Path(artifact["path"])
            actual = sha256_file(path)
            if actual != artifact["sha256"]:
                raise ValueError(
                    f"{method['id']} {name} hash mismatch: expected {artifact['sha256']}, got {actual}"
                )
    if campaign["sentinel_method"] not in ids:
        raise ValueError("sentinel_method must name one compared method")
    schedule(ids, int(protocol["measured_repetitions"]), protocol["order_policy"], int(protocol["seed"]))


def invoke(method: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        method["command"],
        cwd=method.get("cwd"),
        env={**os.environ, **method.get("environment", {})},
        check=True,
        capture_output=True,
        text=True,
    )
    wall = time.perf_counter() - started
    payload = json.loads(completed.stdout)
    if "histories_per_s" not in payload:
        raise ValueError(f"{method['id']} output lacks histories_per_s")
    payload["harness_wall_seconds"] = wall
    payload["stderr"] = completed.stderr
    return payload


def run_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    validate_campaign(campaign)
    methods = {method["id"]: method for method in campaign["methods"]}
    protocol = campaign["protocol"]
    method_ids = list(methods)
    for _ in range(int(protocol["warmups"])):
        for method_id in method_ids:
            invoke(methods[method_id])

    repetitions: dict[str, list[dict[str, Any]]] = {method_id: [] for method_id in method_ids}
    orders = schedule(
        method_ids,
        int(protocol["measured_repetitions"]),
        protocol["order_policy"],
        int(protocol["seed"]),
    )
    for repetition_index, row in enumerate(orders):
        for order_index, method_id in enumerate(row):
            payload = invoke(methods[method_id])
            payload.update({"index": repetition_index, "order_index": order_index})
            repetitions[method_id].append(payload)

    sentinel = campaign["sentinel_method"]
    sentinel_values = [float(row["histories_per_s"]) for row in repetitions[sentinel]]
    aggregates: dict[str, Any] = {}
    for method_id, rows in repetitions.items():
        values = [float(row["histories_per_s"]) for row in rows]
        aggregates[method_id] = {
            **summary(values),
            "ratio_to_sentinel": statistics.median(values) / statistics.median(sentinel_values),
            "bootstrap_ratio_interval_95": paired_bootstrap_ratio(
                values, sentinel_values, seed=int(protocol["seed"])
            ),
        }
    return {
        "schema": "stellarcsg.neutral-command-campaign/v1",
        "case_id": campaign["case_id"],
        "protocol": protocol,
        "common_artifacts": campaign["common_artifacts"],
        "method_metadata": {method_id: methods[method_id]["metadata"] for method_id in method_ids},
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
        result = run_campaign(campaign)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
