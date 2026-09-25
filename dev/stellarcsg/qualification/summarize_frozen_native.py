#!/usr/bin/env python3
"""Summarize same-session native ZTorus sentinel beside frozen-bank lanes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--reduced", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    receipt = json.loads(args.receipt.read_text())
    reduced = json.loads(args.reduced.read_text())
    if reduced.get("errors") or not receipt.get("native_openmc_loader_binding"):
        raise ValueError("reduction errors or native OpenMC binding missing")
    native = receipt.get("native_attempts", [])
    if len(native) != 14 or {(a["repeat"], a["position"]) for a in native} != \
            {(i, side) for i in range(7) for side in ("before", "after")}:
        raise ValueError("seven complete before/after native pairs required")
    values = []
    for attempt in native:
        result = attempt.get("result") or {}
        value = result.get("ns_per_query")
        if attempt.get("exit_code") != 0 or not attempt.get("valid") or \
                result.get("kind") != "native_ztorus_absolute_control" or \
                result.get("queries") != 640000 or not isinstance(value, (int, float)) or \
                not math.isfinite(value) or value <= 0:
            raise ValueError("invalid native attempt")
        values.append(value)
    lanes = reduced["lanes"]
    old = lanes["old"]["metrics"]["distance"]["median_of_bank_means"]
    candidate = lanes["experimental"]["metrics"]["distance"]["median_of_bank_means"]
    if old is None or candidate is None or not lanes["old"]["primary_median_of_7_complete"] or \
            not lanes["experimental"]["primary_median_of_7_complete"]:
        raise ValueError("old/candidate lanes are not complete")
    torus = median(values)
    report = {
        "schema": "stellarcsg.frozen-native-sentinel/v1",
        "receipt_sha256": hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
        "reduced_sha256": hashlib.sha256(args.reduced.read_bytes()).hexdigest(),
        "native_openmc_loader_binding": receipt["native_openmc_loader_binding"],
        "bank_sha256": reduced["bank_hashes"][0],
        "native_ns_per_query": {"median": torus, "min": min(values), "max": max(values),
                                "samples": values},
        "old_ns_per_query": old,
        "candidate_ns_per_query": candidate,
        "old_over_native_sentinel_cost_ratio": old / torus,
        "candidate_over_native_sentinel_cost_ratio": candidate / torus,
        "candidate_over_old_cost_ratio": candidate / old,
        "classification_over_native_ratio": None,
        "normal_over_native_ratio": None,
        "transport_throughput_over_native_ratio": None,
        "comparability": "UNLIKE_GEOMETRY_AND_BANK_SENTINEL_ONLY",
        "claim_boundary": "Native OpenMC ZTorus uses a repeated 64-ray torus bank; the old/candidate coil lanes use the 160-query frozen bank. Ratios are arithmetic absolute-cost sentinels, not matched geometry/transport or correctness evidence.",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("old_over_native_sentinel_cost_ratio",
        "candidate_over_native_sentinel_cost_ratio", "candidate_over_old_cost_ratio")}))


if __name__ == "__main__":
    main()
