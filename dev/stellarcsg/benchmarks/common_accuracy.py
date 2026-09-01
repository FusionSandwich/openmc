#!/usr/bin/env python3
"""Track-neutral finite-surface and nearest-root accuracy metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _nearest(reference: np.ndarray, query: np.ndarray, chunk: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    if reference.ndim != 2 or query.ndim != 2 or reference.shape[1] != 3 or query.shape[1] != 3:
        raise ValueError("point arrays must have shape (N, 3)")
    if not len(reference) or not len(query):
        raise ValueError("point arrays must be nonempty")
    distances = np.empty(len(query), dtype=float)
    indices = np.empty(len(query), dtype=np.int64)
    for start in range(0, len(query), chunk):
        stop = min(start + chunk, len(query))
        delta = query[start:stop, None, :] - reference[None, :, :]
        squared = np.einsum("ijk,ijk->ij", delta, delta)
        local = np.argmin(squared, axis=1)
        indices[start:stop] = local
        distances[start:stop] = np.sqrt(squared[np.arange(stop - start), local])
    return distances, indices


def finite_surface_metrics(
    authoritative_points: np.ndarray,
    candidate_points: np.ndarray,
    authoritative_normals: np.ndarray | None = None,
    candidate_normals: np.ndarray | None = None,
) -> dict[str, float | None]:
    candidate_to_authoritative, candidate_nearest = _nearest(
        authoritative_points, candidate_points
    )
    authoritative_to_candidate, _ = _nearest(candidate_points, authoritative_points)
    both = np.concatenate((candidate_to_authoritative, authoritative_to_candidate))
    normal_error = None
    if authoritative_normals is not None or candidate_normals is not None:
        if authoritative_normals is None or candidate_normals is None:
            raise ValueError("both normal arrays are required")
        if authoritative_normals.shape != authoritative_points.shape:
            raise ValueError("authoritative normals must match authoritative points")
        if candidate_normals.shape != candidate_points.shape:
            raise ValueError("candidate normals must match candidate points")
        left = candidate_normals / np.linalg.norm(candidate_normals, axis=1)[:, None]
        right_raw = authoritative_normals[candidate_nearest]
        right = right_raw / np.linalg.norm(right_raw, axis=1)[:, None]
        cosines = np.clip(np.einsum("ij,ij->i", left, right), -1.0, 1.0)
        normal_error = float(np.degrees(np.arccos(cosines)).max())
    return {
        "hausdorff_two_sided_cm": float(both.max()),
        "surface_distance_rms_cm": float(np.sqrt(np.mean(both * both))),
        "surface_distance_p95_cm": float(np.percentile(both, 95)),
        "normal_angle_max_deg": normal_error,
    }


def relative_error(candidate: float, authoritative: float) -> float:
    if authoritative == 0:
        raise ValueError("authoritative scalar must be nonzero")
    return abs(candidate - authoritative) / abs(authoritative)


def root_metrics(
    authoritative: np.ndarray,
    candidate: np.ndarray,
    tolerance_cm: float,
) -> dict[str, int | float]:
    if authoritative.shape != candidate.shape or authoritative.ndim != 1:
        raise ValueError("root arrays must be equal-length vectors")
    authoritative_hit = np.isfinite(authoritative)
    candidate_hit = np.isfinite(candidate)
    missed = authoritative_hit & ~candidate_hit
    false = ~authoritative_hit & candidate_hit
    paired = authoritative_hit & candidate_hit
    errors = np.abs(authoritative[paired] - candidate[paired])
    wrong = errors > tolerance_cm
    return {
        "wrong_roots": int(np.count_nonzero(wrong)),
        "missed_roots": int(np.count_nonzero(missed)),
        "false_hits": int(np.count_nonzero(false)),
        "root_distance_max_cm": float(errors.max()) if len(errors) else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("authoritative", type=Path, help="NPZ with points and optional normals")
    parser.add_argument("candidate", type=Path, help="NPZ with points and optional normals")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.authoritative) as authoritative, np.load(args.candidate) as candidate:
        metrics = finite_surface_metrics(
            authoritative["points"],
            candidate["points"],
            authoritative.get("normals"),
            candidate.get("normals"),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
