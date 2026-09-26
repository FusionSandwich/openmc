"""Compare sampled compiled implicit seam values with modeled root boxes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--helper-source", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--krawczyk", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    model = json.loads(args.krawczyk.read_text())
    native = json.loads(args.native_receipt.read_text())
    h5_hash = sha256(args.h5)
    if (model.get("h5_sha256") != h5_hash
            or native.get("state") != "BLOCKED_SINGLE_AND_COLLECTION_UNRESOLVED"
            or native.get("solver_probe_complete") is not True
            or h5_hash not in native.get("hashes", {}).values()):
        raise ValueError("model/native/HDF5 identity or native status mismatch")
    results = []
    for member in (2, 3):
        candidates = [row for row in model["results"]
                      if row["member"] == member
                      and row["span"] == row["sample_count"] - 1
                      and row["t_width_cm"] == 1e-6]
        probes = [row for row in native["solver_probes"]
                  if row["member"] == member]
        if len(candidates) != 1 or len(probes) != 1:
            raise ValueError("missing one modeled/native member")
        krawczyk = candidates[0]
        if krawczyk["state"] != "MODEL_UNIQUE_EXISTENCE_CANDIDATE":
            raise ValueError("missing modeled root island")
        tlo, thi = krawczyk["krawczyk"][0]
        lead = float(probes[0]["lead_distance_cm"])
        distances = sorted(set((lead - 1e-11, lead, tlo,
                                (tlo + thi) / 2.0, thi, lead + 1e-11)))
        process = subprocess.run(
            [str(args.executable), str(args.h5), str(member)]
            + [format(value, ".17g") for value in distances],
            capture_output=True, text=True, check=True, timeout=30)
        if process.stderr.strip():
            raise ValueError("compiled implicit helper emitted stderr")
        samples = [json.loads(line) for line in process.stdout.splitlines()]
        if len(samples) != len(distances) or any(
                row["member"] != member or row["t_cm"] != t
                for row, t in zip(samples, distances)):
            raise ValueError("compiled implicit distance echo mismatch")
        by_t = {row["t_cm"]: row for row in samples}
        opposite_endpoint_signs = (by_t[tlo]["implicit_value"]
                                   * by_t[thi]["implicit_value"] < 0.0)
        frame_fields = ("arc_coordinate_cm", "center_cm", "normal",
                        "binormal", "major_radius_cm", "minor_radius_cm")
        sampled_frame_constant = all(
            all(row[field] == samples[0][field] for field in frame_fields)
            for row in samples[1:])
        results.append({"member": member, "span": krawczyk["span"],
                        "model_krawczyk_t_cm": [tlo, thi],
                        "native_diagnostic_lead_cm": lead,
                        "opposite_implicit_signs_at_model_box_edges": (
                            opposite_endpoint_signs),
                        "sampled_frame_constant": sampled_frame_constant,
                        "samples": samples})
        print(member, opposite_endpoint_signs, sampled_frame_constant,
              by_t[tlo]["implicit_value"],
              by_t[thi]["implicit_value"])
    accepted = all(row["opposite_implicit_signs_at_model_box_edges"]
                   and row["sampled_frame_constant"] for row in results)
    report = {"schema": "stellarcsg.compiled-seam-implicit-samples/v1",
              "state": ("SAMPLED_SIGN_BRACKET_STABLE_FRAME" if accepted
                        else "SAMPLED_BRACKET_OR_FRAME_MISMATCH"),
              "source_sha256": sha256(Path(__file__)),
              "helper_source_sha256": sha256(args.helper_source),
              "helper_executable_sha256": sha256(args.executable),
              "static_library_sha256": sha256(args.library),
              "production_source_sha256": sha256(args.production_source),
              "h5_sha256": h5_hash,
              "krawczyk_sha256": sha256(args.krawczyk),
              "native_receipt_sha256": sha256(args.native_receipt),
              "results": results,
              "claim_boundary": "Only six binary64 ray distances per shaped member were sampled through the compiled standalone implicit evaluator. Opposite signs do not prove a continuous root when nearest-centerline frame selection can jump; identical sampled frames do not certify the interval between them or earlier spans. No native OpenMC distance is admitted."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not accepted:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
