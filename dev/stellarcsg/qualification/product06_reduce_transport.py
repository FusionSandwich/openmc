#!/usr/bin/env python3
"""Descriptively reduce a product06 matched transport receipt."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


def number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def completed(attempt: dict[str, Any]) -> bool:
    return attempt.get("completion") == "COMPLETE" and bool(attempt.get("statepoint", {}).get("metrics_valid"))


def state_values(attempt: dict[str, Any]) -> dict[str, Any]:
    return dict(attempt.get("statepoint") or {})


def median_or_none(values: list[float | None]) -> float | None:
    kept = [value for value in values if value is not None]
    return float(median(kept)) if kept else None


def relative(signed: float, reference: float) -> float | None:
    return None if reference == 0.0 else signed / reference


def runtime_value(state: dict[str, Any], *names: str) -> float | None:
    runtime = state.get("runtime_seconds") or {}
    for name in names:
        value = number(runtime.get(name))
        if value is not None:
            return value
    return None


def reduce_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    attempts = list(receipt.get("attempts") or [])
    lanes = sorted({str(attempt.get("lane")) for attempt in attempts if attempt.get("lane") is not None})
    debug = any("-g" in (attempt.get("command") or []) for attempt in attempts)
    tracks = any("-t" in (attempt.get("command") or []) or attempt.get("track_diagnostic") for attempt in attempts)
    timing_label = ("Geometry-debug diagnostic timings" if debug else "Non-debug diagnostic timings") + "; not production-throughput or promotion evidence."
    output: dict[str, Any] = {
        "schema": "stellarcsg.product06.reduce-transport/v1",
        "source_receipt_schema": receipt.get("schema"),
        "claim_boundary": "Descriptive reduction only: no transport qualification, statistical confidence, or inferred root-cause claim.",
        "timing_boundary": timing_label,
        "track_output_excluded_from_timing": tracks,
        "per_lane": {}, "per_seed_pairs": [],
        "source_comparison_raw_differences": [{"seed": row.get("seed"), "status": row.get("status"), "raw_differences": row.get("raw_differences")} for row in receipt.get("comparisons") or []],
        "attempt_statuses": [{key: attempt.get(key) for key in ("lane", "seed", "completion", "exit_code", "timeout", "warnings", "hdf_bindings_unchanged")} | {"metric_errors": state_values(attempt).get("metric_errors")} for attempt in attempts],
    }
    for lane in lanes:
        rows = [attempt for attempt in attempts if attempt.get("lane") == lane]
        valid = [attempt for attempt in rows if completed(attempt)]
        closures = [number(state_values(attempt).get("flux_closure_absolute")) for attempt in valid]
        closure_relative = []
        support: set[int] = set()
        for attempt in valid:
            state = state_values(attempt)
            flux = number(state.get("global_flux"))
            closure = number(state.get("flux_closure_absolute"))
            closure_relative.append(None if closure is None or flux in (None, 0.0) else closure / abs(flux))
            for cell, value in zip(state.get("cell_bins") or [], state.get("cell_flux") or []):
                if number(value) not in (None, 0.0):
                    support.add(int(cell))
        output["per_lane"][lane] = {
            "attempt_count": len(rows), "completed_count": len(valid), "incomplete_count": len(rows) - len(valid),
            "median_active_histories_per_second": median_or_none([number(state_values(row).get("histories_per_active_second")) for row in valid]),
            "median_active_runtime_seconds": median_or_none([runtime_value(state_values(row), "active batches") for row in valid]),
            "median_initialization_runtime_seconds": median_or_none([runtime_value(state_values(row), "total initialization", "initialization") for row in valid]),
            "median_transport_runtime_seconds": median_or_none([runtime_value(state_values(row), "transport") for row in valid]),
            "median_histories_per_transport_second": median_or_none([
                None if runtime_value(state_values(row), "transport") in (None, 0.0) else float(state_values(row).get("n_particles", 0)) / runtime_value(state_values(row), "transport")
                for row in valid]),
            "median_closure_absolute": median_or_none(closures), "median_closure_relative": median_or_none(closure_relative),
            "nonzero_cell_support_count": len(support), "nonzero_cell_bins": sorted(support),
        }
    by_seed: dict[int, dict[str, dict[str, Any]]] = {}
    for attempt in attempts:
        if completed(attempt) and attempt.get("seed") is not None:
            by_seed.setdefault(int(attempt["seed"]), {})[str(attempt["lane"])] = attempt
    for seed, rows in sorted(by_seed.items()):
        exact = rows.get("exact")
        pair: dict[str, Any] = {"seed": seed, "exact_available": exact is not None, "lanes": {}}
        for lane in ("old", "recovered", "exact"):
            attempt = rows.get(lane)
            if attempt is None:
                pair["lanes"][lane] = {"status": "MISSING_OR_INCOMPLETE"}
                continue
            state = state_values(attempt)
            values: dict[str, Any] = {"status": "COMPLETE"}
            if exact is not None:
                exact_state = state_values(exact)
                for label, key in (("active_hps_ratio_lane_over_exact", "histories_per_active_second"),):
                    numerator, denominator = number(state.get(key)), number(exact_state.get(key))
                    values[label] = None if numerator is None or denominator in (None, 0.0) else numerator / denominator
                numerator = number((state.get("runtime_seconds") or {}).get("active batches"))
                denominator = number((exact_state.get("runtime_seconds") or {}).get("active batches"))
                values["active_runtime_ratio_lane_over_exact"] = None if numerator is None or denominator in (None, 0.0) else numerator / denominator
                numerator = runtime_value(state, "transport")
                denominator = runtime_value(exact_state, "transport")
                values["transport_runtime_ratio_lane_over_exact"] = None if numerator is None or denominator in (None, 0.0) else numerator / denominator
                bins, flux = state.get("cell_bins") or [], state.get("cell_flux") or []
                reference_bins, reference_flux = exact_state.get("cell_bins") or [], exact_state.get("cell_flux") or []
                if bins != reference_bins or len(flux) != len(reference_flux):
                    values["tally_difference_status"] = "IDENTITY_OR_SHAPE_MISMATCH"
                else:
                    values["tally_difference_status"] = "AVAILABLE"
                    values["cell_tally_differences_against_exact"] = [
                        {"cell_id": int(cell), "signed": float(value) - float(reference), "relative": relative(float(value) - float(reference), float(reference))}
                        for cell, value, reference in zip(bins, flux, reference_flux)]
            pair["lanes"][lane] = values
        recovered, old = rows.get("recovered"), rows.get("old")
        if recovered is not None and old is not None:
            recovered_transport = runtime_value(state_values(recovered), "transport")
            old_transport = runtime_value(state_values(old), "transport")
            pair["recovered_over_old_transport_runtime_ratio"] = None if recovered_transport is None or old_transport in (None, 0.0) else recovered_transport / old_transport
        else:
            pair["recovered_over_old_transport_runtime_ratio"] = None
        output["per_seed_pairs"].append(pair)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("--output must not overwrite an existing reduction")
    receipt = json.loads(args.receipt.read_text())
    result = reduce_receipt(receipt)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "lanes": len(result["per_lane"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
