"""Run a bounded GCC binary80 Newton trace against analytic seam samples.

The helper copies source arithmetic and reads public compiled powers. Its
agreement with compiled local coordinates is observational, not a proof of
the continuous strip or of earlier swept-surface roots.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("executable", "helper-source", "library",
                 "production-source", "h5", "stationary", "contraction",
                 "prior-samples", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    stationary = json.loads(args.stationary.read_text())
    contraction = json.loads(args.contraction.read_text())
    prior = json.loads(args.prior_samples.read_text())
    if (stationary["state"] != "MODEL_LOCAL_STATIONARY_MINIMA_ENCLOSED"
            or contraction["state"]
            != "REAL_SAFEGUARDED_NEWTON_REACHES_ANGLE_CELL"
            or contraction["stationary_sha256"] != sha256(args.stationary)
            or prior["h5_sha256"] != sha256(args.h5)
            or stationary["h5_sha256"] != sha256(args.h5)):
        raise ValueError("input identities or states disagree")
    prior_by_member = {int(row["member"]): row for row in prior["results"]}
    results = []
    for model in stationary["results"]:
        member = int(model["member"])
        tlo, thi = model["distance_strip_cm"]
        distances = {float(row["t_cm"])
                     for row in prior_by_member[member]["samples"]}
        distances.update(tlo + (thi - tlo) * k / 32 for k in range(33))
        distances = sorted(distances)
        process = subprocess.run(
            [str(args.executable), str(args.h5), str(member)]
            + [format(t, ".17g") for t in distances],
            capture_output=True, text=True, check=True, timeout=45)
        if process.stderr.strip():
            raise ValueError("Newton helper emitted stderr")
        rows = []
        for line in process.stdout.splitlines():
            row = json.loads(line)
            decimal_row = json.loads(line, parse_float=Decimal)
            row["loop_u_decimal"] = str(decimal_row["loop_u"])
            row["best_u_decimal"] = str(decimal_row["best_u"])
            rows.append(row)
        if (len(rows) != len(distances)
                or any(row["member"] != member or row["t_cm"] != t
                       for row, t in zip(rows, distances))):
            raise ValueError("Newton helper sample echo mismatch")
        expected_q = model["separate_round_angle_hex"][0]
        q_mismatches = [row for row in rows if row["q_hex"] != expected_q]
        stops = sorted({row["stop"] for row in rows})
        arcs = sorted({row["compiled_arc_coordinate_cm"] for row in rows})
        centers = {tuple(row["compiled_center_cm"]) for row in rows}
        results.append({
            "member": member, "sample_count": len(rows),
            "expected_q_hex": expected_q,
            "q_mismatch_count": len(q_mismatches),
            "q_mismatch_preview": q_mismatches[:5],
            "minimum_iterations": min(row["iterations"] for row in rows),
            "maximum_iterations": max(row["iterations"] for row in rows),
            "minimum_midpoint_steps": min(row["midpoint_steps"]
                                          for row in rows),
            "maximum_midpoint_steps": max(row["midpoint_steps"]
                                          for row in rows),
            "minimum_newton_steps": min(row["newton_steps"] for row in rows),
            "maximum_newton_steps": max(row["newton_steps"] for row in rows),
            "first_small_iteration_range": [
                min(row["first_small_iteration"] for row in rows),
                max(row["first_small_iteration"] for row in rows)],
            "maximum_abs_loop_residual": max(
                abs(row["loop_residual"]) for row in rows),
            "stops": stops,
            "compiled_arc_values": arcs,
            "compiled_center_count": len(centers),
            "rows": rows,
        })
        print(member, len(rows), len(q_mismatches),
              results[-1]["maximum_iterations"], stops,
              len(centers), flush=True)
    if [row["member"] for row in results] != [2, 3]:
        raise ValueError("expected both shaped members")
    observed = all(row["q_mismatch_count"] == 0
                   and row["compiled_center_count"] == 1
                   and all(math.isfinite(item["loop_residual"])
                           for item in row["rows"])
                   for row in results)
    report = {
        "schema": "stellarcsg.compiled-seam-newton-samples/v1",
        "state": "SAMPLED_BINARY80_ANGLE_CELL_STABLE" if observed
                 else "SAMPLED_MISMATCH_OR_FRAME_CHANGE",
        "source_sha256": sha256(Path(__file__)),
        "helper_source_sha256": sha256(args.helper_source),
        "helper_executable_sha256": sha256(args.executable),
        "static_library_sha256": sha256(args.library),
        "production_source_sha256": sha256(args.production_source),
        "h5_sha256": sha256(args.h5),
        "stationary_sha256": sha256(args.stationary),
        "contraction_sha256": sha256(args.contraction),
        "prior_samples_sha256": sha256(args.prior_samples),
        "results": results,
        "claim_boundary": "The GCC binary80 helper copies the last-span stationary/Newton source arithmetic using public compiled powers and samples 33 evenly spaced strip points plus prior root-box/lead probes per member. q agrees with the real-model angle cell and compiled local-coordinate centers stay fixed at those points. It does not enclose unsampled x, prove the helper is identical to every optimized library instruction, certify BVH traversal/rounded implicit continuity, or admit a native hit."
    }
    args.output.write_text(json.dumps(report, indent=2,
                                      allow_nan=False) + "\n")
    if not observed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
