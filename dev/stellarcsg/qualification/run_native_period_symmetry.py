"""Run a hash-bound finite-grid native quarter-turn covariance diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--static-library", required=True, type=Path)
    parser.add_argument("--original-h5", required=True, type=Path)
    parser.add_argument("--frame-h5", required=True, type=Path)
    parser.add_argument("--exact-h5", required=True, type=Path)
    parser.add_argument("--original-manifest", required=True, type=Path)
    parser.add_argument("--frame-manifest", required=True, type=Path)
    parser.add_argument("--exact-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    h5 = {name: getattr(args, name + "_h5") for name in ("original", "frame", "exact")}
    manifests = {name: getattr(args, name + "_manifest") for name in h5}
    inputs = [args.binary, args.static_library, *h5.values(), *manifests.values()]
    for path in inputs:
        if not path.is_file():
            parser.error(f"missing input: {path}")
    parsed = {name: json.loads(path.read_text()) for name, path in manifests.items()}
    for name in h5:
        if parsed[name]["input_hashes"]["h5_sha256"] != sha256(h5[name]):
            raise ValueError(f"{name} manifest does not bind its HDF5")
    families = parsed["original"]["families"]
    if any(parsed[name]["families"] != families for name in ("frame", "exact")):
        raise ValueError("rotational families differ across the inputs")
    lines = []
    for family in families:
        members = family["full_device_members"]
        if len(members) != 4:
            raise ValueError("rotational family is not a four-member cycle")
        lines.extend(f"{members[0]} {successor} {turns}"
                     for turns, successor in enumerate(members[1:], start=1))
    if len(lines) != 36 or len(set(lines)) != 36:
        raise ValueError("expected 36 unique canonical-to-image pairs")
    args.output.mkdir(parents=True)
    pair_file = args.output / "pairs.txt"
    pair_file.write_text("\n".join(lines) + "\n")
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    summaries = {}
    for name, path in h5.items():
        command = [str(args.binary.resolve()), str(path.resolve()), str(pair_file.resolve())]
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=240, check=False)
        (args.output / f"{name}-stdout.jsonl").write_text(result.stdout)
        (args.output / f"{name}-stderr.txt").write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f"{name} native probe failed: {result.stderr.strip()}")
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        if len(rows) != len(lines) or any(row["samples_per_scale"] != [64, 64, 64]
                                           for row in rows):
            raise RuntimeError(f"{name} native probe returned incomplete rows")
        for row, line in zip(rows, lines):
            canonical, image, turns = line.split()
            if (row["canonical"], row["image"], row["turns"]) != \
                    (canonical, image, int(turns)):
                raise RuntimeError(f"{name} native probe pair order mismatch")
        summaries[name] = {
            "pair_count": len(rows),
            "samples_per_scale": len(rows) * 64,
            "max_abs_implicit_difference_by_scale": [
                max(row["max_abs_implicit_difference"][i] for row in rows)
                for i in range(3)],
            "sign_disagreements_by_scale": [
                sum(row["sign_disagreements"][i] for row in rows)
                for i in range(3)],
        }
    source = Path(__file__).with_name("probe_native_period_symmetry.cpp")
    receipt = {
        "schema": "stellarcsg.native-period-symmetry-sample/v1",
        "state": "SAMPLED_NATIVE_IMPLICIT_COVARIANCE_ONLY",
        "scales": [0.99, 1.0, 1.01],
        "span_ids": [0, 64, 128, 255],
        "fractions": [0.0, 1.0e-8, 0.5, 1.0 - 1.0e-8],
        "alpha_count": 4,
        "summary": summaries,
        "affinity": sorted(os.sched_getaffinity(0)),
        "hashes": {str(path.resolve()): sha256(path) for path in
                   [*inputs, source, Path(__file__), pair_file]},
        "claim_boundary": "Finite-grid comparison of the current compiled implicit evaluator at rotated corresponding points. No continuous floating enclosure, source winding-pack fidelity, periodic-plane ownership, nearest-root proof, transport or performance qualification.",
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
