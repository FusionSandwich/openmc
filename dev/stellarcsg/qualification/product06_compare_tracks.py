#!/usr/bin/env python3
"""Compare diagnostic OpenMC all-track HDF5 outputs outside timing campaigns."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import h5py
import numpy as np


TRACK_NAME = re.compile(r"^track_(\d+)_(\d+)_(\d+)$")
NUMERIC_FIELDS = ("r", "u", "E", "time", "wgt")
DISCRETE_FIELDS = ("cell_id", "cell_instance", "material_id")
REQUIRED_FIELDS = set(NUMERIC_FIELDS + DISCRETE_FIELDS)


def track_datasets(path: Path) -> dict[str, np.ndarray]:
    with h5py.File(path, "r") as handle:
        names = sorted(name for name in handle if TRACK_NAME.fullmatch(name))
        result = {name: np.asarray(handle[name]) for name in names}
    for name, values in result.items():
        if values.dtype.names is None or not REQUIRED_FIELDS <= set(values.dtype.names):
            raise ValueError(f"{path}:{name} lacks required track state fields")
    return result


def numeric_delta(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)))) if left.size else 0.0


def first_difference(reference: np.ndarray, candidate: np.ndarray, tolerance: float) -> dict[str, object] | None:
    for index, (left, right) in enumerate(zip(reference, candidate)):
        fields: dict[str, object] = {}
        for field in DISCRETE_FIELDS:
            if int(left[field]) != int(right[field]):
                fields[field] = {"exact": int(left[field]), "candidate": int(right[field])}
        for field in NUMERIC_FIELDS:
            delta = np.asarray(right[field], dtype=float) - np.asarray(left[field], dtype=float)
            if np.any(~np.isfinite(delta)) or np.max(np.abs(delta), initial=0.0) > tolerance:
                fields[field] = {"exact": np.asarray(left[field]).tolist(), "candidate": np.asarray(right[field]).tolist(), "signed_delta": delta.tolist()}
        if fields:
            return {"event_index": index, "fields": fields}
    return None


def compare_lane(exact_file: Path, candidate_file: Path, tolerance: float) -> dict[str, object]:
    exact, candidate = track_datasets(exact_file), track_datasets(candidate_file)
    result: dict[str, object] = {"exact_history_count": len(exact), "candidate_history_count": len(candidate),
                                 "missing_from_candidate": sorted(set(exact) - set(candidate)), "extra_in_candidate": sorted(set(candidate) - set(exact)),
                                 "shared": []}
    for name in sorted(set(exact) & set(candidate)):
        left, right = exact[name], candidate[name]
        entry: dict[str, object] = {"track": name, "exact_step_count": len(left), "candidate_step_count": len(right),
                                    "exact_discrete_fields": {field: np.asarray(left[field]).tolist() for field in DISCRETE_FIELDS},
                                    "candidate_discrete_fields": {field: np.asarray(right[field]).tolist() for field in DISCRETE_FIELDS}}
        if len(left) != len(right):
            entry["first_difference"] = {"event_index": min(len(left), len(right)), "reason": "step_count"}
        else:
            entry["max_abs_differences"] = {field: numeric_delta(left[field], right[field]) for field in NUMERIC_FIELDS}
            entry["first_difference"] = first_difference(left, right, tolerance)
        result["shared"].append(entry)
    return result


def compare_campaign(campaign: Path, tolerance: float) -> dict[str, object]:
    result: dict[str, object] = {"schema": "stellarcsg.product06.compare-tracks/v1",
        "claim_boundary": "Diagnostic track comparison only; track output is excluded from timing comparisons and this result is not a transport qualification.",
        "numeric_tolerance": tolerance, "seeds": []}
    for seed_folder in sorted(path for path in campaign.glob("seed-*") if path.is_dir()):
        exact = seed_folder / "exact" / "tracks.h5"
        seed: dict[str, object] = {"seed_folder": seed_folder.name, "exact_tracks": str(exact), "lanes": {}}
        if not exact.is_file():
            seed["status"] = "EXACT_TRACKS_MISSING"
        else:
            seed["status"] = "AVAILABLE"
            for lane in ("old", "recovered"):
                candidate = seed_folder / lane / "tracks.h5"
                seed["lanes"][lane] = {"status": "TRACKS_MISSING"} if not candidate.is_file() else {"status": "COMPARED", **compare_lane(exact, candidate, tolerance)}
        result["seeds"].append(seed)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--numeric-tolerance", type=float, default=0.0)
    args = parser.parse_args()
    if args.output.exists() or args.numeric_tolerance < 0.0:
        raise ValueError("output must be new and numeric tolerance nonnegative")
    result = compare_campaign(args.campaign, args.numeric_tolerance)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "seeds": len(result["seeds"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
