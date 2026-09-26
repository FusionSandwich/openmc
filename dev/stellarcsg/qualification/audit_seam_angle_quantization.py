"""Bind the seam Krawczyk boxes to binary64 angle spacing in native arithmetic.

The executable reproduces the production angle expressions independently of
the surface class. This is a diagnostic, not a compiled-surface root proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--cpp-source", type=Path, required=True)
    parser.add_argument("--production-source", type=Path, required=True)
    parser.add_argument("--krawczyk", type=Path, required=True)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    earlier = json.loads(args.krawczyk.read_text())
    if (earlier.get("state") != "EXPERIMENTAL_RECONSTRUCTED_MODEL_ONLY"
            or earlier.get("h5_sha256") != sha256(args.h5)):
        raise ValueError("Krawczyk/HDF5 identity mismatch")
    process = subprocess.run([str(args.executable)], capture_output=True,
                             text=True, check=True, timeout=20)
    if process.stderr.strip():
        raise ValueError("helper emitted stderr")
    native_rows = [json.loads(line) for line in process.stdout.splitlines()]
    if len(native_rows) != 2 or {row["member"] for row in native_rows} != {2, 3}:
        raise ValueError("unexpected member rows")
    results = []
    for native in native_rows:
        member = native["member"]
        matches = [row for row in earlier["results"]
                   if row["member"] == member
                   and row["span"] == native["span"]
                   and row["t_width_cm"] == 1e-6]
        if len(matches) != 1 or matches[0]["state"] != "MODEL_UNIQUE_EXISTENCE_CANDIDATE":
            raise ValueError("missing modeled root box")
        root = matches[0]
        count = native["count"]
        if (native["span"] != count - 1 or root["sample_count"] != count
                or not root["strict_inside"] or root["contraction_norm_inf"] >= 1):
            raise ValueError("span or root box mismatch")
        two_pi = 2.0 * 3.141592653589793238462643383279502884
        step = two_pi / float(count)
        angle_min = step * float(count - 1)
        angle_max = angle_min + step
        scale = 1.0 / (angle_max - angle_min)
        for value, name in ((two_pi, "two_pi"), (angle_min, "angle_min"),
                            (angle_max, "angle_max"), (scale, "scale")):
            if value.hex() != native[f"{name}_hex"]:
                raise ValueError(f"native {name} differs from reproduced expression")
        samples = {row["label"]: row for row in native["samples"]}
        if set(samples) != {"two_below", "predecessor", "endpoint", "successor"}:
            raise ValueError("missing angle-neighbor sample")
        predecessor = math.nextafter(angle_max, -math.inf)
        if float.fromhex(samples["predecessor"]["angle_hex"]) != predecessor:
            raise ValueError("predecessor is not adjacent to endpoint")
        for sample in samples.values():
            angle = float.fromhex(sample["angle_hex"])
            u = (angle - angle_min) * scale
            if u != float.fromhex(sample["u_hex"]) or u != sample["u"]:
                raise ValueError("helper local-u mapping disagrees")
        pred_u = samples["predecessor"]["u"]
        end_u = samples["endpoint"]["u"]
        root_lo, root_hi = root["krawczyk"][1]
        if not (pred_u < root_lo <= root_hi < end_u):
            raise ValueError("root box does not fit the representable-angle gap")
        results.append({"member": member, "span": count - 1,
                        "sample_count": count,
                        "modeled_root_u": [root_lo, root_hi],
                        "predecessor_u": pred_u,
                        "endpoint_u": end_u,
                        "gap_u": end_u - pred_u,
                        "predecessor_angle_hex": samples["predecessor"]["angle_hex"],
                        "endpoint_angle_hex": samples["endpoint"]["angle_hex"],
                        "endpoint_equals_two_pi": angle_max == two_pi,
                        "state": "NO_REPRESENTABLE_ANGLE_IN_MODELED_ROOT_BOX"})
    report = {"schema": "stellarcsg.seam-angle-quantization/v1",
              "state": "NATIVE_ARITHMETIC_DIAGNOSTIC_ONLY",
              "source_sha256": sha256(Path(__file__)),
              "helper_source_sha256": sha256(args.cpp_source),
              "helper_executable_sha256": sha256(args.executable),
              "production_source_sha256": sha256(args.production_source),
              "krawczyk_sha256": sha256(args.krawczyk),
              "h5_sha256": sha256(args.h5),
              "helper_stdout": native_rows,
              "results": results,
              "claim_boundary": "The helper reproduces native angle arithmetic but does not inspect a CompiledSweptSplineSurface instance, enclose frame evaluation, or certify a native root. Modeled root boxes lie between representable angle inputs; a production continuous-root method must handle that gap."}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    for row in results:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
